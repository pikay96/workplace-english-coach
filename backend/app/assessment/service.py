import asyncio

from app.assessment.context import INSTRUCTIONS, assessment_context
from app.assessment.validation import validate_result
from app.conversation.context import encode
from app.observability import failure, metric
from app.sessions.models import AssessmentResult, Session, new_id
from app.sessions.repository import Repository
from app.sessions.transitions import Rejected
from app.voice.inference import Inference


async def assess(repo: Repository, snapshot: Session):
    request_id, frozen_hash = snapshot.assessment.request_id, snapshot.assessment.frozen_hash
    attempt_id = new_id()

    def begin(s):
        if s.assessment.request_id != request_id or s.assessment.status != "pending":
            raise Rejected("assessment_claimed")
        s.assessment.attempt_id = attempt_id
        s.assessment.status = "running"
        s.assessment.deadline = repo.clock() + repo.config.assessment_timeout_seconds
        s.assessment.model = repo.config.assessment_model

    snapshot = await repo.update(snapshot.guest_id, snapshot.id, begin)

    def matching(s):
        if (
            s.assessment.request_id != request_id
            or s.assessment.attempt_id != attempt_id
            or s.assessment.frozen_hash != frozen_hash
            or s.assessment.status != "running"
        ):
            raise Rejected("stale_assessment")

    try:
        result = await Inference(repo.config).structured(
            AssessmentResult,
            INSTRUCTIONS,
            encode(assessment_context(snapshot)),
            model=repo.config.assessment_model,
            timeout=repo.config.assessment_timeout_seconds,
            validate=lambda r: validate_result(snapshot, r),
        )

        def commit(s):
            matching(s)
            if s.assessment.deadline <= repo.clock():
                raise Rejected("assessment_expired")
            s.assessment.result = result
            s.assessment.status = "ready"
            s.assessment.error = None

        await repo.update(snapshot.guest_id, snapshot.id, commit)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        failure("assessment_attempt_failed", error)

        def fail(s):
            matching(s)
            s.assessment.status = "unavailable"
            s.assessment.error = "Assessment unavailable. Retry from your saved words."
            if s.phase == "coaching":
                s.substate = "unavailable"

        try:
            await repo.update(snapshot.guest_id, snapshot.id, fail)
        except Exception:
            pass
        metric("assessment_unavailable", operation_id=request_id)
