import pytest
from pydantic import ValidationError

from app.sessions.models import OpeningProposal


@pytest.mark.parametrize("prompt", ["Welcome us.", "How are you? What's next?", "Your turn."])
def test_opening_requires_one_question_for_the_learner(prompt):
    with pytest.raises(ValidationError):
        OpeningProposal(situation="A meeting.", setup="Everyone is here.", prompt=prompt)


def test_opening_setup_cannot_add_an_extra_question():
    with pytest.raises(ValidationError):
        OpeningProposal(
            situation="A meeting.", setup="Is everyone here?", prompt="Could you get us started?"
        )


def test_opening_accepts_a_direct_question():
    proposal = OpeningProposal(
        situation="A meeting.", setup="Everyone is here.", prompt="Could you get us started?"
    )
    assert proposal.prompt == "Could you get us started?"
