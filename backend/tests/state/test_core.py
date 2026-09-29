import asyncio

import pytest

from app.sessions.models import Command, Input, Transcript, TurnProposal, TutorMessage, new_id
from app.sessions.repository import Unavailable
from app.sessions.transitions import Rejected, accept, command, freeze


def proposal(count, goal=True):
    action = (
        {
            "kind": "coaching",
            "acknowledgment": "Thanks for welcoming us.",
            "bridge": "Let's look at your wording.",
        }
        if count == 3 or count == 2 and goal
        else {
            "kind": "follow_up",
            "acknowledgment": "Thanks.",
            "question": "What would you like us to decide?",
        }
    )
    return TurnProposal(
        contribution_kind="answer", relation="new_answer", goal_demonstrated=goal, action=action
    )


async def save_answer(repo, session, count, goal=True):
    value = Input(status="submitting", capture_seconds=8)

    def stage(s):
        s.input = value

    await repo.update(session.guest_id, session.id, stage)

    def commit(s):
        accept(
            s,
            value.id,
            Transcript(
                text="Good to see everyone. Let's agree on next steps.",
                source_identity=s.participant or "test",
            ),
            proposal(count, goal),
            repo.clock(),
            86400,
        )

    return await repo.update(session.guest_id, session.id, commit), commit


@pytest.mark.redis
async def test_complete_path_duplicate_finish_review(repo, session):
    session.lifecycle = "in_progress"
    session.messages = [
        TutorMessage(
            generation_id=session.generation_id,
            text="Shall we start?",
            kind="opening",
            delivery="completed",
        )
    ]
    session.question_id = session.messages[0].id
    session = await repo.create(session, new_id())
    session, _ = await save_answer(repo, session, 1)
    session, duplicate = await save_answer(repo, session, 2)
    await asyncio.gather(*[repo.update(session.guest_id, session.id, duplicate) for _ in range(6)])
    saved = await repo.get(session.guest_id, session.id)
    assert len(saved.answers) == 2 and saved.phase == "coaching"
    cmd = Command(command_id=new_id(), expected_revision=saved.revision, type="finish")
    saved = await repo.update(
        saved.guest_id, saved.id, lambda s: command(s, cmd, repo.clock(), 86400)
    )
    assert saved.lifecycle == "completed" and saved.assessment.status == "pending"
    assert len((await repo.list(saved.guest_id))[0].answers) == 2


@pytest.mark.redis
async def test_three_answer_limit_and_invalid_early_close(repo, session):
    await repo.create(session, new_id())
    session, _ = await save_answer(repo, session, 1, False)
    session, _ = await save_answer(repo, session, 2, False)
    session, _ = await save_answer(repo, session, 3, False)
    assert len(session.answers) == 3 and session.phase == "coaching"
    with pytest.raises(Rejected):
        await save_answer(repo, session, 4)


@pytest.mark.redis
async def test_delete_expiry_and_isolation_never_resurrect(repo, session):
    await repo.create(session, new_id())
    with pytest.raises(Unavailable):
        await repo.get(new_id(), session.id)
    await repo.delete(session.guest_id, session.id)
    with pytest.raises(Unavailable):
        await repo.update(session.guest_id, session.id, freeze)
    session.id = new_id()
    await repo.create(session, new_id())
    repo.clock = lambda: session.expires_at + 1
    with pytest.raises(Unavailable):
        await repo.update(session.guest_id, session.id, freeze)


@pytest.mark.redis
async def test_no_retention_renewal_and_stale_fences(repo, session):
    await repo.create(session, new_id())
    expiry = session.expires_at
    await repo.get(session.guest_id, session.id)
    await repo.list(session.guest_id)
    saved = await repo.update(
        session.guest_id, session.id, lambda s: setattr(s, "notice", "Result available")
    )
    assert saved.expires_at == expiry
    with pytest.raises(Rejected):
        await repo.update(session.guest_id, session.id, freeze, epoch=new_id())
    with pytest.raises(Rejected):
        await repo.update(session.guest_id, session.id, freeze, generation=new_id())
