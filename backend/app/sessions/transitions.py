"""Pure domain rules; callers provide time, ownership and compare-and-swap."""

import hashlib
import json

from app.sessions.models import (
    Answer,
    Close,
    Command,
    FocusedRetry,
    FollowUp,
    Helper,
    Input,
    Receipt,
    Session,
    Transcript,
    TurnProposal,
    TutorMessage,
    new_id,
)


class Rejected(Exception):
    def __init__(self, code: str = "conflict"):
        self.code = code
        super().__init__(code)


def activity(session: Session, now: float, ttl: int):
    session.last_practice_at = now
    session.expires_at = now + ttl


def cancel_output(session: Session):
    session.generation_id = new_id()
    for message in session.messages:
        if message.delivery in ("pending", "playing"):
            message.delivery = "interrupted"


def freeze(session: Session):
    freeze_retry(session)
    if not session.answers or session.assessment.frozen_hash:
        return
    manifest = {
        "answers": [answer.model_dump() for answer in session.answers],
        "situation": session.situation,
        "messages": [
            m.model_dump()
            for m in session.messages
            if m.kind in ("opening", "follow_up", "bridge", "help")
            and not m.retry_id
            and not m.superseded
        ],
    }
    session.assessment.frozen_hash = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode()
    ).hexdigest()
    session.assessment.request_id = new_id()
    session.assessment.status = "pending"


def active_answers(session):
    return session.retries[-1].answers if session.phase == "retry" else session.answers


def freeze_retry(session, *, finishing=False):
    if not session.retries:
        return
    retry = session.retries[-1]
    at_boundary = any(m.retry_id == retry.id and m.kind == "bridge" for m in session.messages)
    if not retry.answers or retry.assessment.frozen_hash or not (at_boundary or finishing):
        return
    retry.assessment.frozen_hash = hashlib.sha256(retry.model_dump_json().encode()).hexdigest()
    retry.assessment.request_id = new_id()
    retry.assessment.status = "pending"


def command(session: Session, value: Command, now: float, ttl: int) -> Receipt:
    if value.command_id in session.receipts:
        return session.receipts[value.command_id]
    if value.expected_revision != session.revision:
        raise Rejected()
    if value.type not in ("finish", "retry_operation"):
        if value.connection_epoch != session.connection_epoch:
            raise Rejected("stale_connection")
    if session.lifecycle == "completed" and value.type != "retry_operation":
        raise Rejected("completed")
    if value.type in ("pause", "finish"):
        had_unsent_speech = session.input is not None and session.input.first_speech_at is not None
        session.input = None
        session.pending_command = None
        cancel_output(session)
        if session.phase in ("coaching", "retry") or value.type == "finish":
            freeze(session)
        session.lifecycle = "paused" if value.type == "pause" else "completed"
        if value.type == "finish":
            freeze_retry(session, finishing=True)
            session.completed_at = now
            activity(session, now, ttl)
        session.notice = (
            "Your unsent answer was discarded. Accepted answers are saved."
            if had_unsent_speech
            else "Your accepted answers are saved."
        )
    elif value.type == "retry_operation":
        if (
            session.helper
            and session.helper.status == "unavailable"
            and session.lifecycle == "paused"
        ):
            session.helper = Helper(generation_id=session.generation_id)
        elif session.assessment.status == "unavailable":
            session.assessment.request_id = new_id()
            session.assessment.status = "pending"
            session.assessment.error = None
        elif session.retries and session.retries[-1].assessment.status == "unavailable":
            session.retries[-1].assessment.request_id = new_id()
            session.retries[-1].assessment.status = "pending"
        elif session.lifecycle == "in_progress" and session.substate == "unavailable":
            session.pending_command = value
        else:
            raise Rejected("invalid_action")
    elif value.type == "hint":
        session.input = None
        session.pending_command = None
        cancel_output(session)
        if session.phase in ("coaching", "retry"):
            freeze(session)
        session.lifecycle = "paused"
        session.helper = Helper(generation_id=session.generation_id)
        session.notice = (
            "Practice paused for a hint. Unsent words were discarded. Resume when ready."
        )
        activity(session, now, ttl)
    elif value.type == "focused_retry":
        if (
            session.lifecycle != "in_progress"
            or session.phase != "coaching"
            or not session.assessment.result
        ):
            raise Rejected("coaching_required")
        if len(session.retries) >= 12:
            raise Rejected("retry_limit")
        result = session.assessment.result
        target_id = value.target_note_id or result.retry_priority.note_id
        target = next((n for n in result.strengths + result.issues if n.id == target_id), None)
        if not target:
            raise Rejected("invalid_target")
        cancel_output(session)
        session.input = None
        session.phase, session.substate = "retry", "opening"
        session.retries.append(FocusedRetry(target_note_id=target.id, target=target.suggestion))
        session.pending_command = value
        session.notice = None
        activity(session, now, ttl)
    elif value.type in ("mute", "unmute", "replay", "continue_answer", "expression"):
        if session.lifecycle != "in_progress":
            raise Rejected("paused")
        if value.type == "mute":
            session.capture_muted = True
            if session.input:
                if session.input.first_speech_at is not None:
                    session.notice = "Microphone off. Your unsent words were discarded."
                session.input = None
                session.pending_command = None
                cancel_output(session)
                session.substate = "ready"
        elif value.type == "unmute":
            session.capture_muted = False
            # A later explicit Unmute authorizes listening after a pending replay.
            session.replay_restore_capture = True
            if session.substate == "ready":
                open_input(session)
        elif value.type in ("replay", "expression"):
            if not session.messages:
                raise Rejected("playback_unavailable")
            session.replay_restore_capture = session.input is not None and not session.capture_muted
            session.input = None
            cancel_output(session)
            if value.type == "expression":
                from app.content import purpose

                if not value.expression_id:
                    raise Rejected("invalid_expression")
                session.messages.append(
                    TutorMessage(
                        generation_id=session.generation_id,
                        kind="help",
                        text=getattr(purpose(session.purpose_id), value.expression_id),
                        retry_id=session.retries[-1].id if session.phase == "retry" else None,
                    )
                )
            session.pending_command = value
            session.substate = "thinking"
            session.notice = "Unsent words were discarded for replay."
            activity(session, now, ttl)
        else:
            if (
                session.phase != "roleplay"
                or session.assessment.frozen_hash
                or not session.answers
                or session.substate != "listening"
                or not session.input
                or session.input.id != value.input_id
            ):
                raise Rejected("continuation_unavailable")
            remaining = 120 - session.answers[-1].capture_seconds
            if remaining <= 0:
                raise Rejected("answer_limit_reached")
            session.input = Input(
                continuation_of=session.answers[-1].id, max_capture_seconds=remaining
            )
            session.notice = "Continue your previous answer. Its remaining time is preserved."
    else:
        if session.lifecycle != "in_progress":
            raise Rejected("paused")
        if not session.input or value.input_id != session.input.id:
            raise Rejected("stale_input")
        capped = session.input.status == "awaiting_limit_confirmation"
        if value.type == "done" and (capped or session.input.status != "open"):
            raise Rejected("stale_input")
        if value.type in ("use_answer", "try_again") and not capped:
            raise Rejected("invalid_action")
        session.pending_command = value
        if value.type != "try_again":
            session.input.status = "sealing" if value.type == "done" else "submitting"
    receipt = Receipt(
        command_id=value.command_id, revision=session.revision + 1, input_id=value.input_id
    )
    session.receipts[value.command_id] = receipt
    # Bounded metadata, never used as an alternative accepted-answer ledger.
    if len(session.receipts) > 256:
        del session.receipts[next(iter(session.receipts))]
    return receipt


def validate_turn(session: Session, proposal: TurnProposal):
    retry = session.retries[-1] if session.phase == "retry" and session.retries else None
    if session.phase not in ("roleplay", "retry") or (
        retry.assessment.frozen_hash if retry else session.assessment.frozen_hash
    ):
        raise Rejected("exchange_frozen")
    answers = active_answers(session)
    if proposal.contribution_kind != "answer":
        if proposal.action.kind != "help":
            raise Rejected("invalid_proposal")
        return
    continuation = proposal.relation == "continuation"
    if continuation:
        if not answers or not session.input:
            raise Rejected("continuation_unavailable")
        if answers[-1].capture_seconds + session.input.capture_seconds > 120:
            raise Rejected("answer_limit_reached")
    elif session.input and session.input.continuation_of:
        raise Rejected("continuation_required")
    count = len(answers) + (0 if continuation else 1)
    maximum, minimum = (2, 1) if retry else (3, 2)
    required = (
        "coaching"
        if count == maximum or (count >= minimum and proposal.goal_demonstrated)
        else "follow_up"
    )
    if count > maximum or proposal.action.kind != required:
        raise Rejected("invalid_turn_budget")


def accept(
    session: Session,
    input_id: str,
    transcript: Transcript,
    proposal: TurnProposal,
    now: float,
    ttl: int,
):
    answers = active_answers(session)
    retry = session.retries[-1] if session.phase == "retry" else None
    if input_id in session.receipts or any(a.input_id == input_id for a in answers):
        return
    if not session.input or session.input.id != input_id:
        raise Rejected("stale_input")
    if session.input.status != "submitting":
        raise Rejected("input_not_submitted")
    validate_turn(session, proposal)
    if not transcript.text.strip():
        raise Rejected("empty_input")
    if proposal.contribution_kind == "answer":
        if proposal.relation == "continuation":
            answer = answers[-1]
            answer.revision += 1
            answer.transcript.text += " " + transcript.text
            answer.transcript.segment_ids.extend(transcript.segment_ids)
            if transcript.status == "unclear":
                answer.transcript.status = "unclear"
            answer.capture_seconds += session.input.capture_seconds
            answer.capture_limited |= session.input.capture_limited
            # Keep delivery truth, but exclude the replaced question from future context.
            for message in reversed(session.messages):
                if message.id == answer.question_id:
                    break
                if message.kind in ("follow_up", "help"):
                    message.superseded = True
        else:
            answer = Answer(
                input_id=input_id,
                question_id=session.question_id or "",
                transcript=transcript,
                capture_seconds=session.input.capture_seconds,
                capture_limited=session.input.capture_limited,
            )
            answers.append(answer)
        session.receipts[input_id] = Receipt(
            command_id=input_id,
            input_id=input_id,
            answer_id=answer.id,
            revision=session.revision + 1,
        )
    activity(session, now, ttl)
    action = proposal.action
    if isinstance(action, FollowUp):
        text = f"{action.acknowledgment} {action.question}".strip()
        kind = "follow_up"
    elif isinstance(action, Close):
        text = f"{action.acknowledgment} {action.bridge}"
        kind = "bridge"
        if not retry:
            session.phase = "coaching"
    else:
        text, kind = action.text, "help"
    message = TutorMessage(
        generation_id=session.generation_id,
        text=text,
        kind=kind,
        retry_id=retry.id if retry else None,
    )
    session.messages.append(message)
    if kind == "follow_up":
        session.question_id = message.id
        if retry:
            retry.question_id = message.id
    session.input = None
    session.pending_command = None
    session.substate = "speaking"


def open_input(session: Session):
    if (
        session.lifecycle == "in_progress"
        and not session.capture_muted
        and (session.phase != "coaching" or session.assessment.result)
    ):
        session.input = Input()
        session.substate = "listening"
    elif session.capture_muted:
        session.input = None
        session.substate = "ready"
