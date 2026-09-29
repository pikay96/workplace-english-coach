from app.sessions.models import AssessmentResult, Session


def validate_result(session: Session, result: AssessmentResult) -> AssessmentResult:
    answers = {answer.id: answer for answer in session.answers}
    evidence = []
    for dimension in (result.dimensions.naturalness, result.dimensions.workplace_tone):
        if dimension.status == "scored":
            if dimension.score is None or not dimension.evidence:
                raise ValueError("A score requires real evidence")
            for reference in dimension.evidence:
                answer = answers.get(reference.turn_id)
                if answer is None or answer.transcript.status != "reliable":
                    raise ValueError("A score requires reliable original wording")
        elif dimension.score is not None:
            raise ValueError("Unavailable dimensions cannot have scores")
        evidence.extend(dimension.evidence)
    notes = result.strengths + result.issues
    if len({note.id for note in notes}) != len(notes):
        raise ValueError("Note IDs must be unique")
    if result.retry_priority.note_id not in {note.id for note in notes}:
        raise ValueError("Priority must refer to a supported note")
    for note in notes:
        evidence.extend(note.evidence)
    for reference in evidence:
        answer = answers.get(reference.turn_id)
        if not answer or answer.revision != reference.answer_revision:
            raise ValueError("Evidence must resolve to an original answer revision")
        if reference.quote is not None and reference.quote not in answer.transcript.text:
            raise ValueError("Quote must exactly match submitted wording")
    return result
