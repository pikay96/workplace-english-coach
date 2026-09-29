import asyncio
import time
from contextlib import suppress

from livekit.agents import Agent, AgentSession, StopResponse, llm, stt

from app.conversation.coaching import accept_question, answer_question
from app.conversation.context import (
    OPENING_INSTRUCTIONS,
    TURN_INSTRUCTIONS,
    context,
    detector_messages,
    encode,
    validate_opening,
)
from app.observability import failure, metric
from app.sessions.models import (
    ContinuationProposal,
    Input,
    OpeningProposal,
    Session,
    Transcript,
    TurnProposal,
    TutorMessage,
    new_id,
)
from app.sessions.repository import Repository
from app.sessions.transitions import (
    Rejected,
    accept,
    active_answers,
    cancel_output,
    freeze,
    open_input,
    validate_turn,
)
from app.voice.buffer import AnswerBuffer
from app.voice.inference import Inference


class ControlledAgent(Agent):
    def __init__(self, runtime):
        super().__init__(
            instructions="Application-controlled roleplay. Never generate default replies."
        )
        self.runtime = runtime

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        self.runtime.launch_seal(text=new_message.text_content or "")
        raise StopResponse()

    async def stt_node(self, audio, model_settings):
        async def learner_frames():
            async for frame in audio:
                if not self.runtime.accepting:
                    # Manual commit injects silence after microphone input is disabled.
                    # Let STT finalize, while rejecting all further speech/capture.
                    if self.runtime.finalizing and not any(frame.data):
                        yield frame
                    continue
                if self.runtime.buffer:
                    if self.runtime.buffer.duration() >= self.runtime.buffer.limit_seconds:
                        self.runtime.launch_seal(capped=True)
                        continue
                    try:
                        self.runtime.buffer.append(frame)
                    except (BufferError, ValueError):
                        self.runtime.launch_error("Capture unavailable. Try this answer again.")
                        continue
                yield frame

        async for event in Agent.default.stt_node(self, learner_frames(), model_settings):
            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT and self.runtime.buffer:
                self.runtime.buffer.segment_ids.append(new_id())
                self.runtime.buffer.final_segments.append(event.alternatives[0].text)
            yield event


class Runtime:
    def __init__(self, repo: Repository, saved: Session, voice: AgentSession):
        self.repo, self.saved, self.voice = repo, saved, voice
        self.guest, self.identifier, self.epoch = saved.guest_id, saved.id, saved.connection_epoch
        self.models = Inference(repo.config)
        self.buffer: AnswerBuffer | None = None
        self.accepting = False
        self.finalizing = False
        self.seal_task: asyncio.Task | None = None
        self.work_task: asyncio.Task | None = None
        self.output_handle = None
        self.closed = False
        self.lock = asyncio.Lock()
        self.speech_generation: str | None = None

    async def update(self, mutate, generation=None):
        return await self.repo.update(
            self.guest, self.identifier, mutate, epoch=self.epoch, generation=generation
        )

    def launch_seal(self, *, text=None, capped=False):
        if self.seal_task and not self.seal_task.done():
            return
        self.seal_task = asyncio.create_task(self.seal(text=text, capped=capped))

    def launch_error(self, message):
        self.accepting = False
        self.work_task = asyncio.create_task(self.error(message))

    async def error(self, message):
        self.accepting = False
        self.voice.input.set_audio_enabled(False)
        self.voice.clear_user_turn()
        if self.buffer:
            self.buffer.clear()
            self.buffer = None

        def fail(s):
            s.substate = "unavailable"
            s.notice = message
            s.input = None
            s.pending_command = None
            cancel_output(s)

        with suppress(Rejected):
            await self.update(fail)

    async def start(self):
        self.stop_capture()
        if self.saved.phase == "retry":
            await self.start_retry()
            return
        if not self.saved.messages:

            def intent(s):
                s.substate = "opening"
                s.input = None

            saved = await self.update(intent)
            opening = await self.models.structured(
                OpeningProposal,
                OPENING_INSTRUCTIONS,
                encode(context(saved)),
                model=self.repo.config.conversation_model,
                validate=lambda proposal: validate_opening(saved, proposal),
            )

            def save(s):
                s.situation, s.setup = opening.situation, opening.setup
                message = TutorMessage(
                    generation_id=s.generation_id,
                    text=f"{opening.setup} {opening.prompt}",
                    kind="opening",
                )
                s.messages.append(message)
                s.question_id = message.id

            saved = await self.update(save, saved.generation_id)
        else:

            def resume(s):
                s.input = None
                if s.phase == "coaching":
                    s.substate = "assessment_pending" if not s.assessment.result else "ready"

            saved = await self.update(resume)
        if saved.phase == "roleplay":
            await self.speak(saved.messages[-1].id, saved.generation_id)
        elif saved.assessment.result:
            latest = next(
                (
                    m
                    for m in reversed(saved.messages)
                    if m.kind in ("coaching", "coaching_answer", "retry_coaching")
                ),
                None,
            )
            if latest:
                await self.speak(latest.id, saved.generation_id)

    async def start_retry(self):
        saved = await self.repo.get(self.guest, self.identifier)
        retry = saved.retries[-1]
        if retry.assessment.status != "none":
            message = next(
                (
                    m
                    for m in reversed(saved.messages)
                    if m.retry_id == retry.id and m.kind == "retry_coaching"
                ),
                None,
            )
            if retry.assessment.result and message:
                await self.speak(message.id, saved.generation_id)
            else:
                await self.update(
                    lambda s: setattr(
                        s,
                        "substate",
                        "unavailable"
                        if retry.assessment.status == "unavailable"
                        else "assessment_pending",
                    )
                )
            return
        if not retry.situation:
            opening = await self.models.structured(
                OpeningProposal,
                OPENING_INSTRUCTIONS,
                encode(context(saved)),
                model=self.repo.config.conversation_model,
            )

            def save(s):
                current = s.retries[-1]
                if current.id != retry.id:
                    raise Rejected("stale_retry")
                current.situation, current.setup = opening.situation, opening.setup
                message = TutorMessage(
                    generation_id=s.generation_id,
                    kind="opening",
                    text=f"{opening.setup} {opening.prompt}",
                    retry_id=current.id,
                )
                s.messages.append(message)
                s.question_id = current.question_id = message.id
                s.pending_command = None

            saved = await self.update(save, saved.generation_id)
        message = next(
            m for m in reversed(saved.messages) if m.retry_id == retry.id and not m.superseded
        )
        await self.speak(message.id, saved.generation_id)

    def stop_capture(self):
        self.accepting = False
        self.voice.input.set_audio_enabled(False)
        self.voice.clear_user_turn()
        if self.buffer:
            self.buffer.clear()
            self.buffer = None

    async def listen(self, saved):
        self.stop_capture()
        await self.rebuild_detector(saved)
        if not saved.input:
            return

        def authorize(s):
            if (
                s.lifecycle != "in_progress"
                or s.substate != "listening"
                or not s.input
                or s.input.id != saved.input.id
                or s.input.status != "open"
                or s.capture_muted
                or any(m.delivery == "playing" for m in s.messages)
            ):
                raise Rejected("capture_not_open")

        # Recheck ownership/generation after the awaited detector update. Pause or
        # a newer output must not reopen capture from a stale playback receipt.
        await self.update(authorize, saved.generation_id)
        self.buffer = AnswerBuffer(saved.input.id, limit_seconds=saved.input.max_capture_seconds)
        self.accepting = True
        self.voice.input.set_audio_enabled(True)

    async def rebuild_detector(self, saved):
        chat = llm.ChatContext()
        for role, words in detector_messages(saved):
            chat.add_message(role=role, content=words)
        await self.voice.current_agent.update_chat_ctx(chat)

    async def speech_started(self):
        if not self.accepting or not self.buffer:
            return
        if self.output_handle and not self.output_handle.done():
            return
        self.buffer.speech()
        input_id = self.buffer.input_id

        def mark(s):
            if not s.input or s.input.id != input_id:
                raise Rejected("stale_input")
            if s.input.first_speech_at is None:
                s.input.first_speech_at = self.repo.clock()

        try:
            await self.update(mark)
        except Rejected:
            return

    async def seal(self, *, text=None, capped=False):
        async with self.lock:
            current = self.buffer
            if not current or current.sealed:
                return
            current.sealed = True
            duration = current.duration()
            self.accepting = False
            self.voice.input.set_audio_enabled(False)
            input_id = current.input_id
            try:

                def stage(s):
                    if not s.input or s.input.id != input_id:
                        raise Rejected("stale_input")
                    s.input.status = "sealing"
                    s.input.capture_seconds = duration
                    s.input.capture_limited = capped
                    s.substate = "capped" if capped else "thinking"
                    s.pending_command = None

                await self.update(stage)
                if text is None:
                    self.finalizing = True
                    try:
                        async with asyncio.timeout(8):
                            text = await self.voice.commit_user_turn(
                                transcript_timeout=5, stt_flush_duration=2, skip_reply=True
                            )
                            # SDK 1.8.2 resolves commit before its end-of-turn task finishes.
                            # That task still interrupts background say() handles, even with
                            # skip_reply. Settle it before opening input or scheduling a reply.
                            # Pinned SDK seam: session.wait_for_idle() also waits for VAD
                            # silence, which can stay latched when input is disabled just
                            # after a final STT event. Only settle the pending SDK tasks.
                            await self.voice.current_agent._get_activity_or_raise().wait_for_idle(
                                wait_for_user=False
                            )
                    finally:
                        self.finalizing = False
                current.text = text
                if not text.strip():

                    def empty(s):
                        s.notice = "No words were saved. Try the same prompt again."
                        open_input(s)

                    saved = await self.update(empty)
                    current.clear()
                    await self.listen(saved)
                    return
                if capped:

                    def cap(s):
                        if not s.input or s.input.id != input_id:
                            raise Rejected("stale_input")
                        s.input.status = "awaiting_limit_confirmation"
                        s.substate = "capped"

                    await self.update(cap)
                    return
                await self.submit(current)
            except asyncio.CancelledError:
                current.clear()
                raise
            except Rejected as error:
                current.clear()
                if error.code == "answer_limit_reached":
                    await self.error(
                        "Your previous answer reached its time limit. Try the current prompt."
                    )
                elif error.code in ("session_limit", "coaching_limit"):
                    await self.error(
                        "This practice has reached its limit. Finish to keep your results."
                    )
            except Exception as error:
                fresh = await self.repo.get(self.guest, self.identifier)
                if not fresh.input or fresh.input.id != current.input_id:
                    current.clear()
                    return
                failure("answer_unavailable", error)
                if current.text:

                    def pending(s):
                        if not s.input or s.input.id != current.input_id:
                            raise Rejected("stale_input")
                        s.substate = "unavailable"
                        s.pending_command = None
                        s.notice = (
                            "Your answer is not saved yet. Retry while this connection is open."
                        )

                    with suppress(Rejected):
                        await self.update(pending)
                else:
                    await self.error(
                        "Your answer could not be saved. Please repeat the same prompt."
                    )

    async def submit(self, current):
        def intent(s):
            if not s.input or s.input.id != current.input_id:
                raise Rejected("stale_input")
            s.input.status = "submitting"
            s.substate = "thinking"
            s.pending_command = None
            s.generation_id = new_id()

        saved = await self.update(intent)
        transcript = Transcript(
            text=current.text,
            status=current.transcript_status(),
            segment_ids=current.segment_ids.copy(),
            source_identity=saved.participant,
        )
        if saved.phase == "coaching":
            reply = await answer_question(self.models, self.repo.config, saved, transcript)
            saved = await self.update(
                lambda s: accept_question(
                    s,
                    current.input_id,
                    transcript,
                    reply,
                    self.repo.clock(),
                    self.repo.config.session_ttl_seconds,
                ),
                saved.generation_id,
            )
            current.clear()
            self.buffer = None
            await self.speak(saved.messages[-1].id, saved.generation_id)
            return
        answers = active_answers(saved)
        minimum, maximum = (1, 2) if saved.phase == "retry" else (2, 3)
        continuing = saved.input.continuation_of is not None
        prospective = len(answers) + (0 if continuing else 1)

        def valid(proposal):
            try:
                validate_turn(saved, proposal)
            except Rejected as error:
                if error.code == "invalid_turn_budget":
                    raise ValueError(
                        "invalid_turn_budget: select action.kind from action_rules for the "
                        "current contribution_kind and goal_demonstrated value. "
                        "accepted_answer_count excludes current_transcript."
                    ) from None
                if error.code == "invalid_proposal":
                    raise ValueError(
                        "invalid_proposal: help, coaching_question or unusable requires "
                        "action.kind=help; "
                        "an intelligible answer attempt requires contribution_kind=answer."
                    ) from None
                raise ValueError(error.code) from None

        proposal = await self.models.structured(
            ContinuationProposal if continuing else TurnProposal,
            TURN_INSTRUCTIONS,
            encode(
                {
                    **context(saved),
                    "current_transcript": current.text,
                    "current_transcript_status": current.transcript_status(),
                    "current_answer_number_if_accepted": prospective,
                    "action_rules": {
                        "answer_when_goal_demonstrated_true": (
                            "coaching" if prospective >= minimum else "follow_up"
                        ),
                        "answer_when_goal_demonstrated_false": (
                            "coaching" if prospective >= maximum else "follow_up"
                        ),
                        "help": "help",
                        "coaching_question": "help",
                        "unusable": "help",
                    },
                    "continuation": {
                        "selected_answer_id": saved.input.continuation_of,
                        "eligible_answer_id": answers[-1].id if answers else None,
                        "remaining_seconds": 120 - answers[-1].capture_seconds if answers else 120,
                        "rules": "Keep the count for a continuation and recompute its action. "
                        "selected_answer_id marks an explicit continuation interval. "
                        "Otherwise interpret the relation to the current prompt.",
                        "action_when_goal_true": "coaching"
                        if len(answers) >= minimum
                        else "follow_up",
                        "action_when_goal_false": "coaching"
                        if len(answers) >= maximum
                        else "follow_up",
                    },
                }
            ),
            model=self.repo.config.conversation_model,
            validate=valid,
        )
        saved = await self.update(
            lambda s: accept(
                s,
                current.input_id,
                transcript,
                proposal,
                self.repo.clock(),
                self.repo.config.session_ttl_seconds,
            ),
            saved.generation_id,
        )
        current.clear()
        self.buffer = None
        await self.rebuild_detector(saved)
        await self.speak(saved.messages[-1].id, saved.generation_id)

    async def speak(self, message_id, generation, *, restore_capture: bool | None = True):
        playback_id = new_id()

        def begin(s):
            if s.lifecycle != "in_progress":
                raise Rejected("paused")
            message = next(m for m in s.messages if m.id == message_id)
            message.generation_id = s.generation_id
            message.playback_id = playback_id
            message.delivery = "playing"
            s.substate = "thinking"
            s.input = None

        saved = await self.update(begin, generation)
        self.stop_capture()
        message = next(m for m in saved.messages if m.id == message_id)
        generation = saved.generation_id
        self.speech_generation = generation
        started = time.monotonic()
        audio_seconds = 0.0

        async def frames():
            nonlocal audio_seconds
            async for frame in self.models.speech(message.text):
                if audio_seconds == 0:
                    metric(
                        "tts_audio_ready",
                        phase=saved.phase,
                        duration_ms=round((time.monotonic() - started) * 1000),
                    )
                    await self.update(lambda s: setattr(s, "substate", "speaking"), generation)
                audio_seconds += frame.samples_per_channel / frame.sample_rate
                fresh = await self.repo.get(self.guest, self.identifier)
                owner = await self.repo.redis.get(self.repo.lease(self.guest))
                if (
                    fresh.generation_id != generation
                    or fresh.lifecycle != "in_progress"
                    or owner != f"{self.identifier}:{self.epoch}:active"
                ):
                    return
                yield frame
            metric(
                "tts_stream_complete",
                phase=saved.phase,
                duration_ms=round((time.monotonic() - started) * 1000),
                audio_seconds=audio_seconds,
            )

        status, played = "failed", None
        try:
            # First-frame latency is bounded separately by Inference.speech.
            async with asyncio.timeout(90):
                # Alex finishes before answer capture opens. Only explicit controls
                # or ownership loss may cancel this approved output.
                handle = self.voice.say(
                    message.text,
                    audio=frames(),
                    add_to_chat_ctx=False,
                    allow_interruptions=False,
                )
                self.output_handle = handle
                await handle
                metric(
                    "audio_playout_complete",
                    phase=saved.phase,
                    duration_ms=round((time.monotonic() - started) * 1000),
                )
                status = (
                    "interrupted"
                    if handle.interrupted
                    else "failed"
                    if handle.exception()
                    else "completed"
                )
                if status == "completed" and audio_seconds == 0:
                    status = "failed"
                if status == "completed":
                    played = message.text
        except asyncio.CancelledError:
            if self.output_handle:
                self.output_handle.interrupt(force=True)
            raise
        except TimeoutError:
            if self.output_handle:
                self.output_handle.interrupt(force=True)
        except Exception as error:
            failure("playback_failed", error)

        def delivered(s):
            restore = s.replay_restore_capture if restore_capture is None else restore_capture
            msg = next(m for m in s.messages if m.id == message_id)
            if msg.playback_id != playback_id:
                raise Rejected("stale_playback")
            msg.delivery, msg.played_text = status, played
            if status == "failed":
                s.notice = "Alex’s audio could not finish. Your saved words are still available."
            if msg.kind == "bridge" and status in ("completed", "failed"):
                freeze(s)
                s.substate = "assessment_pending"
            elif msg.kind == "retry_coaching" and status == "completed":
                s.phase = "coaching"
                if restore:
                    open_input(s)
                else:
                    s.substate = "ready"
            elif status == "failed":
                s.input = None
                s.substate = "unavailable"
            elif status == "completed" and restore:
                open_input(s)
            else:
                s.substate = "ready"

        with suppress(Rejected):
            delivered_session = await self.update(delivered, generation)
            await self.listen(delivered_session)
        metric(
            "playback",
            operation_id=playback_id,
            phase=saved.phase,
            duration_ms=round((time.monotonic() - started) * 1000),
            audio_seconds=audio_seconds,
        )

    async def tick(self):
        saved = await self.repo.get(self.guest, self.identifier)
        owner = await self.repo.redis.get(self.repo.lease(self.guest))
        admission = await self.repo.redis.zscore(self.repo.capacity_key, saved.room or "")
        if (
            saved.lifecycle != "in_progress"
            or saved.connection_epoch != self.epoch
            or owner != f"{self.identifier}:{self.epoch}:active"
            or admission is None
            or admission <= self.repo.clock()
        ):
            self.closed = True
            return
        self.saved = saved
        if self.buffer and (saved.input is None or saved.input.id != self.buffer.input_id):
            self.stop_capture()
        if (
            saved.input
            and saved.input.status == "open"
            and saved.substate == "listening"
            and not self.buffer
        ):
            await self.listen(saved)
        if self.buffer and not self.buffer.sealed and self.buffer.started is not None:
            elapsed = self.buffer.duration()
            if elapsed >= self.buffer.limit_seconds:
                self.launch_seal(capped=True)
            elif (
                saved.input
                and elapsed + (120 - saved.input.max_capture_seconds) >= 60
                and not saved.input.cue_shown
            ):
                await self.update(
                    lambda s: setattr(s.input, "cue_shown", True) if s.input else None
                )
        pending = saved.pending_command
        if pending and pending.type == "focused_retry":
            await self.cancel_work()
            await self.update(lambda s: setattr(s, "pending_command", None))
            self.work_task = asyncio.create_task(self.start_retry())
        elif pending and pending.type in ("replay", "expression"):
            await self.cancel_work()
            saved = await self.update(lambda s: setattr(s, "pending_command", None))
            message = next(m for m in reversed(saved.messages) if not m.superseded)
            self.work_task = asyncio.create_task(
                self.speak(message.id, saved.generation_id, restore_capture=None)
            )
        elif pending and pending.type == "done":
            self.launch_seal()
        elif pending and pending.type == "try_again":
            if self.buffer:
                self.buffer.clear()

            def retry(s):
                s.pending_command = None
                prior = s.input
                s.input = Input(
                    continuation_of=prior.continuation_of,
                    max_capture_seconds=prior.max_capture_seconds,
                )
                s.substate = "listening"

            await self.listen(await self.update(retry))
        elif pending and pending.type == "use_answer" and self.buffer:
            if not self.work_task or self.work_task.done():
                self.work_task = asyncio.create_task(self.submit(self.buffer))
        elif pending and pending.type == "retry_operation":

            def retry_operation(s):
                s.pending_command = None
                s.notice = None

            await self.update(retry_operation)
            if self.buffer and self.buffer.text:
                self.work_task = asyncio.create_task(self.submit(self.buffer))
            else:
                self.work_task = asyncio.create_task(self.start())
        idle = not any(t and not t.done() for t in (self.work_task, self.seal_task))
        if (
            saved.phase == "coaching"
            and saved.assessment.result
            and idle
            and not any(m.kind == "coaching" for m in saved.messages)
        ):

            def coaching(s):
                s.messages.append(
                    TutorMessage(
                        generation_id=s.generation_id,
                        kind="coaching",
                        text=s.assessment.result.spoken_summary,
                    )
                )

            saved = await self.update(coaching)
            self.work_task = asyncio.create_task(
                self.speak(saved.messages[-1].id, saved.generation_id)
            )
        if saved.phase == "retry" and saved.retries and idle:
            retry = saved.retries[-1]
            if retry.assessment.result:

                def feedback(s):
                    if any(
                        m.retry_id == retry.id and m.kind == "retry_coaching" for m in s.messages
                    ):
                        return
                    result = s.retries[-1].assessment.result
                    s.messages.append(
                        TutorMessage(
                            generation_id=s.generation_id,
                            kind="retry_coaching",
                            retry_id=retry.id,
                            text=(
                                f"{result.observation} {result.suggestion} {result.modeled_example}"
                            ),
                        )
                    )

                saved = await self.update(feedback)
                message = next(m for m in reversed(saved.messages) if m.kind == "retry_coaching")
                # A failed playback waits for an explicit retry instead of looping.
                if message.delivery == "pending":
                    self.work_task = asyncio.create_task(
                        self.speak(message.id, saved.generation_id)
                    )
        for task in (self.work_task, self.seal_task):
            if task and task.done() and not task.cancelled() and task.exception():
                if not isinstance(task.exception(), Rejected):
                    failure("voice_task_unavailable", task.exception())
                    await self.error(
                        "The voice service is unavailable. Your accepted answers are saved."
                    )
                if task == self.work_task:
                    self.work_task = None
                else:
                    self.seal_task = None

    async def cancel_work(self):
        self.stop_capture()
        if self.output_handle and not self.output_handle.done():
            self.output_handle.interrupt(force=True)
        tasks = [t for t in (self.seal_task, self.work_task) if t and not t.done()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.seal_task = self.work_task = None

    async def run(self):
        self.work_task = asyncio.create_task(self.start())
        try:
            while not self.closed:
                await self.tick()
                await asyncio.sleep(0.2)
        finally:
            self.accepting = False
            with suppress(RuntimeError):
                self.voice.input.set_audio_enabled(False)
                self.voice.interrupt(force=True)
                self.voice.clear_user_turn()
            if self.buffer:
                self.buffer.clear()
            tasks = [t for t in (self.seal_task, self.work_task) if t]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
