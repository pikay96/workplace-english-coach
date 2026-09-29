import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from livekit import rtc
from livekit.agents import Agent, StopResponse, llm

from app.sessions.models import Input, new_id
from app.sessions.transitions import command
from app.voice.buffer import AnswerBuffer
from app.voice.runtime import ControlledAgent, Runtime


async def active_runtime(repo, session):
    session.lifecycle = "in_progress"
    session.connection_epoch = new_id()
    session.room = f"practice-{session.id}-{session.connection_epoch}"
    session.input = Input()
    saved = await repo.create(session, new_id())
    await repo.redis.set(
        repo.lease(session.guest_id), f"{session.id}:{session.connection_epoch}:active", ex=60
    )
    await repo.redis.zadd(repo.capacity_key, {session.room: repo.clock() + 60})
    voice = SimpleNamespace(
        input=SimpleNamespace(set_audio_enabled=Mock()),
        clear_user_turn=Mock(),
        commit_user_turn=AsyncMock(return_value="Good morning, everyone."),
        current_agent=SimpleNamespace(
            update_chat_ctx=AsyncMock(),
            _get_activity_or_raise=Mock(return_value=SimpleNamespace(wait_for_idle=AsyncMock())),
        ),
    )
    runtime = Runtime(repo, saved, voice)
    runtime.buffer = AnswerBuffer(saved.input.id)
    runtime.buffer.speech()
    runtime.accepting = True
    return runtime


async def test_sdk_hook_suppresses_automatic_reply():
    runtime = SimpleNamespace(launch_seal=Mock())
    agent = ControlledAgent(runtime)
    message = llm.ChatMessage(role="user", content=["Good morning, everyone."])
    with pytest.raises(StopResponse):
        await agent.on_user_turn_completed(llm.ChatContext(), message)
    runtime.launch_seal.assert_called_once_with(text="Good morning, everyone.")


def test_interim_tail_is_not_reported_as_reliable_final_wording():
    buffer = AnswerBuffer(new_id())
    buffer.final_segments = ["Good morning."]
    buffer.text = "Good morning. Thank you for joining."
    assert buffer.transcript_status() == "unclear"
    buffer.final_segments.append("Thank you for joining.")
    assert buffer.transcript_status() == "reliable"
    buffer.clear()
    assert not buffer.final_segments and buffer.transcript_status() == "unclear"


def test_detector_context_keeps_exchange_order_and_excludes_unheard_words(session):
    from app.conversation.context import detector_messages
    from app.sessions.models import Answer, Transcript, TutorMessage

    first = TutorMessage(
        generation_id=new_id(),
        text="Welcome us.",
        kind="opening",
        delivery="completed",
        played_text="Welcome us.",
    )
    pending = TutorMessage(generation_id=new_id(), text="Unheard prompt.", kind="follow_up")
    session.messages = [first, pending]
    session.answers = [
        Answer(
            input_id=new_id(),
            question_id=first.id,
            capture_seconds=3,
            transcript=Transcript(text="Good morning.", source_identity="fixture"),
        )
    ]
    assert detector_messages(session) == [
        ("assistant", "Welcome us."),
        ("user", "Good morning."),
    ]


async def test_automatic_and_manual_completion_share_one_submission(repo, session):
    runtime = await active_runtime(repo, session)
    runtime.submit = AsyncMock()
    await asyncio.gather(runtime.seal(text="Good morning."), runtime.seal())
    runtime.submit.assert_awaited_once()
    runtime.voice.commit_user_turn.assert_not_awaited()


async def test_cap_retains_final_transcript_until_explicit_choice(repo, session):
    runtime = await active_runtime(repo, session)
    runtime.submit = AsyncMock()
    await runtime.seal(capped=True)
    capped = await repo.get(session.guest_id, session.id)
    assert capped.input.status == "awaiting_limit_confirmation"
    assert capped.answers == []
    runtime.submit.assert_not_awaited()
    assert runtime.buffer.text == "Good morning, everyone."
    runtime.voice.commit_user_turn.assert_awaited_once_with(
        transcript_timeout=5, stt_flush_duration=2, skip_reply=True
    )


async def test_manual_submission_waits_for_sdk_turn_finalization(repo, session):
    runtime = await active_runtime(repo, session)
    sdk_settled = asyncio.Event()
    sdk_waiting = asyncio.Event()

    async def settle(**kwargs):
        assert kwargs == {"wait_for_user": False}
        sdk_waiting.set()
        await sdk_settled.wait()

    runtime.voice.current_agent._get_activity_or_raise().wait_for_idle = settle
    runtime.submit = AsyncMock()
    task = asyncio.create_task(runtime.seal())
    try:
        await asyncio.wait_for(sdk_waiting.wait(), timeout=5)
        runtime.voice.commit_user_turn.assert_awaited_once()
        runtime.submit.assert_not_awaited()
        sdk_settled.set()
        await task
        runtime.submit.assert_awaited_once()
    finally:
        sdk_settled.set()
        await task


async def test_sealed_input_allows_sdk_flush_silence_without_capturing_more_audio(
    repo, session, monkeypatch
):
    runtime = await active_runtime(repo, session)
    runtime.accepting = False
    runtime.finalizing = True
    runtime.buffer.sealed = True
    silence = rtc.AudioFrame.create(16000, 1, 3200)
    speech = rtc.AudioFrame(
        data=b"\x01\x00" * 3200, sample_rate=16000, num_channels=1, samples_per_channel=3200
    )
    seen = []

    async def provider(agent, audio, settings):
        async for frame in audio:
            seen.append(frame)
        if False:
            yield

    async def frames():
        yield speech
        yield silence

    monkeypatch.setattr(Agent.default, "stt_node", provider)
    agent = ControlledAgent(runtime)
    async for _ in agent.stt_node(frames(), None):
        pass
    assert seen == [silence]
    assert not runtime.buffer.pcm


async def test_pause_during_stt_finalization_cannot_restore_discarded_input(repo, session):
    from app.sessions.models import Command

    runtime = await active_runtime(repo, session)
    entered, proceed = asyncio.Event(), asyncio.Event()

    async def finalize(**kwargs):
        entered.set()
        await proceed.wait()
        return "Late final words."

    runtime.voice.commit_user_turn = finalize
    task = asyncio.create_task(runtime.seal(capped=True))
    await entered.wait()
    saved = await repo.get(session.guest_id, session.id)
    value = Command(
        command_id=new_id(),
        expected_revision=saved.revision,
        type="pause",
        connection_epoch=saved.connection_epoch,
    )
    await repo.update(
        session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
    )
    proceed.set()
    await task
    paused = await repo.get(session.guest_id, session.id)
    assert paused.lifecycle == "paused" and paused.input is None and paused.answers == []
    assert not runtime.buffer.pcm and runtime.buffer.text is None


async def test_delayed_speech_start_cannot_interrupt_a_later_reply(repo, session):
    runtime = await active_runtime(repo, session)
    entered, proceed = asyncio.Event(), asyncio.Event()
    update = runtime.update

    async def delayed(mutate, generation=None):
        entered.set()
        await proceed.wait()
        return await update(mutate, generation)

    runtime.update = delayed
    task = asyncio.create_task(runtime.speech_started())
    await entered.wait()
    later_output = Mock()
    later_output.done.return_value = False
    runtime.output_handle = later_output
    proceed.set()
    await task
    later_output.interrupt.assert_not_called()


async def test_queued_speech_cannot_start_after_pause(repo, session):
    from app.sessions.models import Command, TutorMessage
    from app.sessions.transitions import Rejected

    runtime = await active_runtime(repo, session)
    message = TutorMessage(generation_id=session.generation_id, text="Saved words.", kind="opening")
    saved = await repo.update(session.guest_id, session.id, lambda s: s.messages.append(message))
    generation = saved.generation_id
    value = Command(
        command_id=new_id(),
        expected_revision=saved.revision,
        type="pause",
        connection_epoch=saved.connection_epoch,
    )
    await repo.update(
        session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
    )
    with pytest.raises(Rejected):
        await runtime.speak(message.id, generation)
    latest = await repo.get(session.guest_id, session.id)
    assert latest.messages[0].delivery == "interrupted"
    assert latest.messages[0].played_text is None


def controlled_playback(runtime, *, fail=False, buffered=False):
    """Hold actual Runtime.speak at the SDK playback-completion boundary."""
    playing, completed = asyncio.Event(), asyncio.Event()

    async def speech(text):
        yield rtc.AudioFrame.create(24000, 1, 480)

    def say(text, *, audio, **kwargs):
        async def playout():
            async for _ in audio:
                pass
            playing.set()
            await completed.wait()
            if fail:
                raise RuntimeError("Fixture playback failure")

        task = asyncio.create_task(playout())
        task.interrupted = False
        task.interrupt = Mock()
        return task

    if not buffered:
        runtime.models.speech = speech
    runtime.voice.say = Mock(side_effect=say)
    return playing, completed


async def test_pause_during_audio_preparation_never_opens_microphone(repo, session):
    from app.sessions.models import Command, TutorMessage
    from tests.contracts.test_speech import delayed_provider

    runtime = await active_runtime(repo, session)
    message = TutorMessage(
        generation_id=session.generation_id, kind="opening", text="Could you get us started?"
    )
    saved = await repo.update(session.guest_id, session.id, lambda s: s.messages.append(message))
    waiting, release, client = delayed_provider(runtime.models)
    playing, completed = controlled_playback(runtime, buffered=True)
    runtime.work_task = asyncio.create_task(runtime.speak(message.id, saved.generation_id))
    try:
        await asyncio.wait_for(waiting.wait(), 2)
        saved = await repo.get(session.guest_id, session.id)
        assert saved.substate == "thinking" and saved.input is None
        assert not runtime.accepting and not playing.is_set()
        value = Command(
            command_id=new_id(),
            expected_revision=saved.revision,
            connection_epoch=saved.connection_epoch,
            type="pause",
        )
        await repo.update(
            session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
        )
        await runtime.cancel_work()
        saved = await repo.get(session.guest_id, session.id)
        assert saved.input is None and not runtime.accepting
        assert saved.messages[-1].played_text is None
        assert saved.messages[-1].delivery == "interrupted"
        assert not playing.is_set()
        client.aclose.assert_awaited_once()
    finally:
        release.set()
        completed.set()
        await runtime.cancel_work()


@pytest.mark.parametrize("resuming", [False, True])
async def test_opening_and_resume_listen_only_after_playback(repo, session, resuming):
    from app.sessions.models import OpeningProposal, TutorMessage

    runtime = await active_runtime(repo, session)
    runtime.models.structured = AsyncMock(
        return_value=OpeningProposal(
            situation="A meeting.", setup="You are the host.", prompt="Could you get us started?"
        )
    )
    if resuming:
        runtime.saved = await repo.update(
            session.guest_id,
            session.id,
            lambda s: s.messages.append(
                TutorMessage(generation_id=s.generation_id, kind="opening", text="Welcome us.")
            ),
        )
    playing, completed = controlled_playback(runtime)
    task = asyncio.create_task(runtime.start())
    try:
        await asyncio.wait_for(playing.wait(), 2)
        saved = await repo.get(session.guest_id, session.id)
        assert saved.substate == "speaking" and saved.input is None
        assert not runtime.accepting and runtime.buffer is None
        runtime.voice.input.set_audio_enabled.assert_called_with(False)
        await runtime.speech_started()
        runtime.output_handle.interrupt.assert_not_called()
        assert (await repo.get(session.guest_id, session.id)).answers == []
    finally:
        completed.set()
        await task
    saved = await repo.get(session.guest_id, session.id)
    assert saved.messages[0].delivery == "completed"
    assert saved.substate == "listening" and saved.input.status == "open"
    assert saved.input.first_speech_at is None
    assert runtime.accepting and runtime.buffer.started is None
    await runtime.speech_started()
    assert (await repo.get(session.guest_id, session.id)).input.first_speech_at is not None


@pytest.mark.parametrize("outcome", ["completed", "failed", "pause"])
async def test_follow_up_playback_opens_capture_only_on_current_success(repo, session, outcome):
    from app.sessions.models import Command, TutorMessage

    runtime = await active_runtime(repo, session)
    message = TutorMessage(
        generation_id=session.generation_id, kind="follow_up", text="What is our goal?"
    )
    saved = await repo.update(session.guest_id, session.id, lambda s: s.messages.append(message))
    playing, completed = controlled_playback(runtime, fail=outcome == "failed")
    task = asyncio.create_task(runtime.speak(message.id, saved.generation_id))
    try:
        await asyncio.wait_for(playing.wait(), 2)
        assert not runtime.accepting
        assert (await repo.get(session.guest_id, session.id)).input is None
        if outcome == "pause":
            current = await repo.get(session.guest_id, session.id)
            value = Command(
                command_id=new_id(),
                expected_revision=current.revision,
                connection_epoch=current.connection_epoch,
                type="pause",
            )
            await repo.update(
                session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
            )
    finally:
        completed.set()
        await task
    saved = await repo.get(session.guest_id, session.id)
    if outcome == "completed":
        assert saved.input.status == "open" and runtime.accepting
    else:
        assert saved.input is None and not runtime.accepting
        assert saved.messages[-1].delivery == ("failed" if outcome == "failed" else "interrupted")


async def test_stale_speech_start_never_cancels_alex(repo, session):
    runtime = await active_runtime(repo, session)
    output = Mock()
    output.done.return_value = False
    runtime.output_handle = output
    await runtime.speech_started()
    output.interrupt.assert_not_called()


async def test_submitted_answer_waits_for_follow_up_before_listening(repo, session):
    from app.sessions.models import TurnProposal

    session.participant = "fixture"
    runtime = await active_runtime(repo, session)
    runtime.models.structured = AsyncMock(
        return_value=TurnProposal(
            contribution_kind="answer",
            relation="new_answer",
            goal_demonstrated=True,
            action={
                "kind": "follow_up",
                "acknowledgment": "Thanks.",
                "question": "What is our goal?",
            },
        )
    )
    playing, completed = controlled_playback(runtime)
    task = asyncio.create_task(runtime.seal(text="Good morning, everyone."))
    try:
        await asyncio.wait_for(playing.wait(), 2)
        saved = await repo.get(session.guest_id, session.id)
        assert len(saved.answers) == 1 and saved.input is None
        assert not runtime.accepting
        assert all(
            call.args == (False,) for call in runtime.voice.input.set_audio_enabled.call_args_list
        )
    finally:
        completed.set()
        await task
    assert (await repo.get(session.guest_id, session.id)).input.status == "open"
    assert runtime.accepting


async def test_pause_during_detector_preparation_cannot_reopen_capture(repo, session):
    from app.sessions.models import Command
    from app.sessions.transitions import Rejected, open_input

    runtime = await active_runtime(repo, session)
    saved = await repo.update(session.guest_id, session.id, open_input)

    async def pause_while_preparing(chat):
        value = Command(
            command_id=new_id(),
            expected_revision=saved.revision,
            connection_epoch=saved.connection_epoch,
            type="pause",
        )
        await repo.update(
            session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
        )

    runtime.voice.current_agent.update_chat_ctx = pause_while_preparing
    with pytest.raises(Rejected):
        await runtime.listen(saved)
    assert not runtime.accepting and runtime.buffer is None
    runtime.voice.input.set_audio_enabled.assert_called_with(False)


async def test_explicit_continuation_has_same_count_and_constrained_relation(repo, session):
    import json

    from app.sessions.models import Answer, ContinuationProposal, Transcript

    session.participant = "fixture"
    session.answers.append(
        Answer(
            input_id=new_id(),
            question_id=new_id(),
            capture_seconds=8,
            transcript=Transcript(text="Thanks for coming.", source_identity="fixture"),
        )
    )
    runtime = await active_runtime(repo, session)
    await repo.update(
        session.guest_id, session.id, lambda s: setattr(s.input, "continuation_of", s.answers[0].id)
    )
    runtime.buffer.text = "I also appreciate your time."
    runtime.models.structured = AsyncMock(
        return_value=ContinuationProposal(
            contribution_kind="answer",
            relation="continuation",
            goal_demonstrated=True,
            action={"kind": "follow_up", "acknowledgment": "Thanks.", "question": "What's next?"},
        )
    )
    runtime.speak = AsyncMock()
    await runtime.submit(runtime.buffer)
    args = runtime.models.structured.call_args.args
    assert args[0] is ContinuationProposal
    data = json.loads(args[2])
    assert data["current_answer_number_if_accepted"] == 1
    assert data["action_rules"]["answer_when_goal_demonstrated_true"] == "follow_up"
    saved = await repo.get(session.guest_id, session.id)
    assert len(saved.answers) == 1 and saved.answers[0].revision == 2


async def test_unmute_during_replay_waits_for_playback_then_opens_input(repo, session):
    from app.sessions.models import Command, TutorMessage

    runtime = await active_runtime(repo, session)

    def prepare(s):
        s.capture_muted = True
        s.replay_restore_capture = False
        s.messages.append(
            TutorMessage(generation_id=s.generation_id, kind="follow_up", text="Saved question")
        )

    saved = await repo.update(session.guest_id, session.id, prepare)
    playing, completed = controlled_playback(runtime)
    task = asyncio.create_task(
        runtime.speak(saved.messages[-1].id, saved.generation_id, restore_capture=None)
    )
    try:
        await asyncio.wait_for(playing.wait(), 2)
        saved = await repo.get(session.guest_id, session.id)
        value = Command(
            command_id=new_id(),
            expected_revision=saved.revision,
            connection_epoch=saved.connection_epoch,
            type="unmute",
        )
        saved = await repo.update(
            session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
        )
        assert saved.input is None and not runtime.accepting
    finally:
        completed.set()
        await task
    assert (await repo.get(session.guest_id, session.id)).input.status == "open"
    assert runtime.accepting


async def test_continuation_cue_and_cap_use_total_answer_duration(repo, session):
    runtime = await active_runtime(repo, session)
    await repo.update(
        session.guest_id,
        session.id,
        lambda s: setattr(s.input, "max_capture_seconds", 70),
    )
    runtime.buffer.limit_seconds = 70
    runtime.buffer.duration = Mock(return_value=9)
    runtime.launch_seal = Mock()
    await runtime.tick()
    assert not (await repo.get(session.guest_id, session.id)).input.cue_shown
    runtime.buffer.duration.return_value = 10
    await runtime.tick()
    assert (await repo.get(session.guest_id, session.id)).input.cue_shown
    runtime.launch_seal.assert_not_called()
    runtime.buffer.duration.return_value = 70
    await runtime.tick()
    runtime.launch_seal.assert_called_once_with(capped=True)
