import asyncio
from unittest.mock import AsyncMock

import pytest

from app.assessment.service import assess
from app.sessions.models import Command, Input, TutorMessage, new_id
from app.sessions.ownership import claim
from app.sessions.recovery import expire_assessment, recover, sweep_rooms
from app.sessions.transitions import Rejected, command, freeze
from tests.contracts.test_assessment import result_for


class Gateway:
    def __init__(self):
        self.remove_room = AsyncMock()
        self.dispatch = AsyncMock()

    def token(self, saved):
        return "fixture"


async def create(repo, source):
    session = source.model_copy(deep=True)
    session.id, session.guest_id = new_id(), new_id()
    return await repo.create(session, new_id())


async def test_concurrent_admission_rejects_fifth_and_pause_releases_slot(repo, session):
    gateway = Gateway()
    sessions = [await create(repo, session) for _ in range(5)]
    results = await asyncio.gather(
        *(claim(repo, s.guest_id, s.id, gateway) for s in sessions), return_exceptions=True
    )
    accepted = [result[0] for result in results if isinstance(result, tuple)]
    rejected = [result for result in results if isinstance(result, Rejected)]
    assert len(accepted) == 4 and [r.code for r in rejected] == ["capacity_full"]
    assert await repo.redis.zcard(repo.capacity_key) == 4
    saved = accepted[0]
    value = Command(
        command_id=new_id(),
        expected_revision=saved.revision,
        type="pause",
        connection_epoch=saved.connection_epoch,
    )
    await repo.update(saved.guest_id, saved.id, lambda s: command(s, value, repo.clock(), 86400))
    waiting = next(s for s in sessions if s.id not in {s.id for s in accepted})
    await claim(repo, waiting.guest_id, waiting.id, gateway)
    assert await repo.redis.zcard(repo.capacity_key) == 4


async def test_dispatch_failure_releases_room_slot_and_normalizes_state(repo, session):
    gateway = Gateway()
    gateway.dispatch.side_effect = RuntimeError("fixture dispatch failure")
    await repo.create(session, new_id())
    with pytest.raises(RuntimeError):
        await claim(repo, session.guest_id, session.id, gateway)
    saved = await repo.get(session.guest_id, session.id)
    assert saved.lifecycle == "paused" and saved.input is None
    assert await repo.redis.zcard(repo.capacity_key) == 0
    assert await repo.redis.get(repo.lease(session.guest_id)) is None
    gateway.remove_room.assert_awaited_once_with(saved.room)


async def test_late_dispatch_after_delete_never_returns_token(repo, session):
    gateway = Gateway()
    await repo.create(session, new_id())

    async def delete_during_dispatch(saved):
        await repo.delete(saved.guest_id, saved.id)

    gateway.dispatch.side_effect = delete_during_dispatch
    with pytest.raises(Rejected):
        await claim(repo, session.guest_id, session.id, gateway)
    assert await repo.redis.zcard(repo.capacity_key) == 0


@pytest.mark.parametrize("state", ["open", "sealing", "submitting", "awaiting_limit_confirmation"])
async def test_lost_owner_discards_only_unsent_input_and_preserves_prompt(repo, session, state):
    session.lifecycle = "in_progress"
    session.input = Input(status=state, first_speech_at=repo.clock())
    prompt = TutorMessage(
        generation_id=new_id(), text="Saved prompt", kind="follow_up", delivery="playing"
    )
    session.messages.append(prompt)
    session.question_id = prompt.id
    await repo.create(session, new_id())
    saved = await recover(repo, session.guest_id, session.id)
    assert saved.lifecycle == "paused" and saved.input is None
    assert saved.question_id == prompt.id and saved.messages[0].text == "Saved prompt"
    assert saved.messages[0].delivery == "interrupted"
    assert "not saved" in saved.notice and saved.expires_at == session.expires_at


async def test_valid_owner_is_not_paused_by_recovery_and_expiry_revokes_room(repo, session):
    gateway = Gateway()
    await repo.create(session, new_id())
    saved, _ = await claim(repo, session.guest_id, session.id, gateway)
    assert (await recover(repo, session.guest_id, session.id)).lifecycle == "in_progress"
    now = repo.clock()
    repo.clock = lambda: now + repo.config.voice_lease_seconds + 1
    await sweep_rooms(repo, gateway)
    gateway.remove_room.assert_awaited_once_with(saved.room)
    with pytest.raises(Rejected):
        await repo.heartbeat(session.guest_id, session.id, saved.connection_epoch)
    assert (await recover(repo, session.guest_id, session.id)).lifecycle == "paused"


async def test_expired_assessment_cannot_commit_late_and_explicit_retry_is_bounded(
    repo, session, monkeypatch
):
    result = result_for(session)
    freeze(session)
    await repo.create(session, new_id())
    entered, proceed = asyncio.Event(), asyncio.Event()

    async def provider(*args, **kwargs):
        entered.set()
        await proceed.wait()
        return result

    monkeypatch.setattr("app.assessment.service.Inference.structured", provider)
    task = asyncio.create_task(assess(repo, session))
    await entered.wait()
    running = await repo.get(session.guest_id, session.id)
    repo.clock = lambda: running.assessment.deadline + 1
    await repo.update(session.guest_id, session.id, lambda s: expire_assessment(s, repo.clock()))
    proceed.set()
    await task
    failed = await repo.get(session.guest_id, session.id)
    assert failed.assessment.status == "unavailable" and failed.assessment.result is None
    assert failed.expires_at == session.expires_at
    value = Command(command_id=new_id(), expected_revision=failed.revision, type="retry_operation")
    retry = await repo.update(
        session.guest_id, session.id, lambda s: command(s, value, repo.clock(), 86400)
    )
    await assess(repo, retry)
    ready = await repo.get(session.guest_id, session.id)
    assert ready.assessment.status == "ready" and ready.assessment.result == result
    assert ready.expires_at == session.expires_at
