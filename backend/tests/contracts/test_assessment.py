import pytest
from pydantic import ValidationError

from app.assessment.validation import validate_result
from app.sessions.models import Answer, AssessmentResult, Transcript, new_id


def result_for(session):
    answer = Answer(
        input_id=new_id(),
        question_id=new_id(),
        capture_seconds=3,
        transcript=Transcript(
            text="Thank you for joining. Let's discuss next steps.", source_identity="fixture"
        ),
    )
    session.answers.append(answer)
    evidence = {
        "turn_id": answer.id,
        "answer_revision": 1,
        "observation": "The welcome acknowledges the participants.",
        "quote": "Thank you for joining.",
    }
    dimension = {
        "status": "scored",
        "score": 4,
        "basis": "wording",
        "explanation": "The welcome suits a team meeting.",
        "evidence": [evidence],
    }
    note = {
        "id": "welcome",
        "observation": "The welcome is appropriate.",
        "evidence": [evidence],
        "suggestion": "Make the desired outcome specific.",
        "example": "Let's agree on the next two steps.",
        "reason": "A concrete outcome gives focus.",
    }
    return AssessmentResult.model_validate(
        {
            "dimensions": {"naturalness": dimension, "workplace_tone": dimension},
            "strengths": [note],
            "issues": [],
            "retry_priority": {"note_id": "welcome", "suggestion": note["suggestion"]},
            "spoken_summary": (
                "Your welcome acknowledged everyone. Try making the outcome more specific."
            ),
            "modeled_example": note["example"],
            "takeaway": "Welcome people, then name a specific outcome.",
        }
    )


def test_accepts_grounded_result_and_rejects_fabricated_quote(session):
    result = result_for(session)
    assert validate_result(session, result) is result
    result.dimensions.naturalness.evidence[0].quote = "Invented words"
    with pytest.raises(ValueError, match="exactly"):
        validate_result(session, result)


def test_rejects_unclear_scored_wording_and_wrong_revision(session):
    result = result_for(session)
    session.answers[0].transcript.status = "unclear"
    with pytest.raises(ValueError, match="reliable"):
        validate_result(session, result)
    session.answers[0].transcript.status = "reliable"
    session.answers[0].revision = 2
    with pytest.raises(ValueError, match="revision"):
        validate_result(session, result)


def test_rejects_audio_dimension_and_score_for_unavailable(session):
    result = result_for(session)
    payload = result.model_dump()
    payload["dimensions"]["pronunciation"] = payload["dimensions"]["naturalness"]
    with pytest.raises(ValidationError):
        AssessmentResult.model_validate(payload)
    result.dimensions.naturalness.status = "not_enough_detail"
    with pytest.raises(ValueError, match="cannot have scores"):
        validate_result(session, result)
