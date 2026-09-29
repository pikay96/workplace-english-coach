import pytest

from app.sessions.models import Input, Transcript, new_id
from app.sessions.transitions import Rejected, accept, freeze
from tests.state.test_core import proposal, save_answer


async def test_continuation_preserves_answer_id_and_budget_under_duplicate_submission(
    repo, session
):
    session.lifecycle = "in_progress"
    await repo.create(session, new_id())
    first, _ = await save_answer(repo, session, 1)
    original = first.answers[0].model_copy(deep=True)
    fragment = Input(status="submitting", capture_seconds=7, continuation_of=original.id)
    await repo.update(session.guest_id, session.id, lambda s: setattr(s, "input", fragment))
    continuing = proposal(1)
    continuing.relation = "continuation"

    def commit(s):
        accept(
            s,
            fragment.id,
            Transcript(text="Thanks for your time.", source_identity="test"),
            continuing,
            repo.clock(),
            86400,
        )

    result = await repo.update(session.guest_id, session.id, commit)
    await repo.update(session.guest_id, session.id, commit)
    result = await repo.get(session.guest_id, session.id)
    assert len(result.answers) == 1
    assert result.answers[0].id == original.id and result.answers[0].revision == 2
    assert result.answers[0].capture_seconds == 15
    assert result.answers[0].transcript.text == original.transcript.text + " Thanks for your time."
    assert result.messages[-2].superseded


async def test_continuation_cannot_exceed_budget_or_revise_frozen_exchange(repo, session):
    await repo.create(session, new_id())
    saved, _ = await save_answer(repo, session, 1)
    value = Input(status="submitting", capture_seconds=113)
    saved.input = value
    continuing = proposal(1)
    continuing.relation = "continuation"
    with pytest.raises(Rejected, match="answer_limit_reached"):
        accept(
            saved,
            value.id,
            Transcript(text="More words", source_identity="test"),
            continuing,
            repo.clock(),
            86400,
        )
    saved.input.capture_seconds = 5
    freeze(saved)
    with pytest.raises(Rejected, match="exchange_frozen"):
        accept(
            saved,
            value.id,
            Transcript(text="More words", source_identity="test"),
            continuing,
            repo.clock(),
            86400,
        )
    assert saved.answers[0].revision == 1
