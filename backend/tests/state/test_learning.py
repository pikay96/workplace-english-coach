import asyncio
from unittest.mock import AsyncMock

import pytest

from app.assessment.targeted import assess_retry, validate_targeted
from app.conversation.coaching import accept_question
from app.conversation.helpers import generate_hint
from app.sessions.models import CoachingReply, Command, Input, TargetedResult, Transcript, new_id
from app.sessions.transitions import Rejected, accept, command, freeze
from tests.contracts.test_assessment import result_for
from tests.state.test_core import proposal


def cmd(saved, kind, **kwargs):
    return Command(
        command_id=new_id(),
        expected_revision=saved.revision,
        connection_epoch=saved.connection_epoch,
        type=kind,
        **kwargs,
    )


@pytest.mark.parametrize("closes_at", [1, 2])
async def test_focused_retry_uses_separate_evidence_budget_and_preserves_scores(
    repo, session, monkeypatch, closes_at
):
    original = result_for(session)
    freeze(session)
    session.assessment.result, session.assessment.status = original, "ready"
    session.phase, session.lifecycle = "coaching", "in_progress"
    baseline = session.assessment.model_dump_json()
    await repo.create(session, new_id())
    value = cmd(session, "focused_retry")
    saved = await repo.update(
        session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
    )
    for count in range(1, closes_at + 1):

        def answer(s, count=count):
            s.input = Input(status="submitting", capture_seconds=4)
            turn = proposal(2 if count == closes_at else 1)
            turn.goal_demonstrated = count == closes_at
            accept(
                s,
                s.input.id,
                Transcript(text="Let's agree on two next steps.", source_identity="test"),
                turn,
                repo.clock(),
                86400,
            )

        saved = await repo.update(session.guest_id, session.id, answer)
    saved = await repo.update(session.guest_id, session.id, freeze)
    retry = saved.retries[-1]
    assert len(retry.answers) == closes_at and retry.assessment.status == "pending"
    assert not {a.id for a in retry.answers} & {a.id for a in saved.answers}
    result = TargetedResult(
        target_note_id=retry.target_note_id,
        status="demonstrated",
        observation="The outcome is specific.",
        suggestion="Keep naming the intended outcome.",
        modeled_example="Let's agree on two next steps.",
        evidence=[
            {
                "turn_id": retry.answers[0].id,
                "answer_revision": 1,
                "quote": "two next steps",
                "observation": "A concrete outcome.",
            }
        ],
    )
    validate_targeted(retry, result)
    monkeypatch.setattr(
        "app.assessment.targeted.Inference.structured", AsyncMock(return_value=result)
    )
    await assess_retry(repo, saved, retry.id)
    saved = await repo.get(session.guest_id, session.id)
    assert saved.assessment.model_dump_json() == baseline
    assert saved.retries[-1].assessment.result == result
    with pytest.raises(Rejected, match="exchange_frozen"):
        await repo.update(session.guest_id, session.id, answer)
    result.evidence[0].turn_id = saved.answers[0].id
    with pytest.raises(ValueError):
        validate_targeted(retry, result)


def test_coaching_questions_never_become_original_answers_or_change_scores(session):
    session.assessment.result = result_for(session)
    session.phase, session.lifecycle = "coaching", "in_progress"
    session.input = Input(status="submitting")
    before = session.assessment.model_dump_json()
    input_id = session.input.id
    reply = CoachingReply(text="Naming an outcome helps colleagues focus.", evidence=[])
    accept_question(
        session,
        input_id,
        Transcript(text="Why is that useful?", source_identity="test"),
        reply,
        session.created_at,
        86400,
    )
    accept_question(
        session,
        input_id,
        Transcript(text="Why is that useful?", source_identity="test"),
        reply,
        session.created_at,
        86400,
    )
    assert len(session.coaching_turns) == 1 and len(session.answers) == 1
    assert session.phase == "coaching" and session.assessment.model_dump_json() == before


async def test_hint_pauses_discards_cap_and_late_hint_cannot_survive_finish(
    repo, session, monkeypatch
):
    session.lifecycle = "in_progress"
    session.input = Input(status="awaiting_limit_confirmation")
    await repo.create(session, new_id())
    value = cmd(session, "hint")
    paused = await repo.update(
        session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
    )
    assert paused.lifecycle == "paused" and paused.input is None and not paused.answers
    entered, proceed = asyncio.Event(), asyncio.Event()

    async def provider(*args, **kwargs):
        from app.sessions.models import Help

        entered.set()
        await proceed.wait()
        return Help(kind="help", text="Try naming the outcome.")

    monkeypatch.setattr("app.conversation.helpers.Inference.structured", provider)
    task = asyncio.create_task(generate_hint(repo, paused))
    await entered.wait()
    saved = await repo.get(session.guest_id, session.id)
    finish = cmd(saved, "finish")
    await repo.update(
        session.guest_id, session.id, lambda s: command(s, finish, repo.clock(), 86400)
    )
    proceed.set()
    result = await task
    assert result.lifecycle == "completed" and result.helper.text is None
