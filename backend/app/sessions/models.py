from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def new_id() -> str:
    return uuid4().hex


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)


Text = Annotated[str, Field(min_length=1, max_length=4000)]
Identifier = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class Transcript(Model):
    text: str = Field(max_length=24000)
    status: Literal["reliable", "unclear"] = "reliable"
    segment_ids: list[str] = Field(default_factory=list, max_length=1000)
    source_identity: str


class Answer(Model):
    id: str = Field(default_factory=new_id)
    input_id: str
    revision: int = 1
    question_id: str
    transcript: Transcript
    capture_seconds: float = Field(ge=0, le=120)
    capture_limited: bool = False


class TutorMessage(Model):
    id: str = Field(default_factory=new_id)
    generation_id: str
    text: Text
    kind: Literal[
        "opening", "follow_up", "bridge", "coaching", "help", "coaching_answer", "retry_coaching"
    ]
    delivery: Literal["pending", "playing", "completed", "interrupted", "failed"] = "pending"
    playback_id: str | None = None
    played_text: str | None = None
    superseded: bool = False
    retry_id: str | None = None


class Input(Model):
    id: str = Field(default_factory=new_id)
    status: Literal["open", "sealing", "awaiting_limit_confirmation", "submitting"] = "open"
    first_speech_at: float | None = None
    cue_shown: bool = False
    capture_seconds: float = 0
    capture_limited: bool = False
    continuation_of: str | None = None
    max_capture_seconds: float = Field(default=120, gt=0, le=120)


class Evidence(Model):
    turn_id: str = Field(description="Copy an accepted_answers[].id exactly.")
    answer_revision: int = Field(description="Copy the revision of that accepted answer.")
    observation: Text
    quote: str | None = Field(default=None, max_length=2000)


class Dimension(Model):
    status: Literal["scored", "not_enough_detail", "transcript_unclear", "assessment_unavailable"]
    score: int | None = Field(default=None, ge=1, le=5, strict=True)
    basis: Literal["wording"]
    explanation: Text
    evidence: list[Evidence] = Field(max_length=12)


class Dimensions(Model):
    naturalness: Dimension
    workplace_tone: Dimension


class Note(Model):
    id: str = Field(
        min_length=1,
        max_length=40,
        description="Unique note key, such as note_1. This is not an answer ID.",
    )
    observation: Text
    evidence: list[Evidence] = Field(min_length=1, max_length=12)
    suggestion: Text
    example: Text
    reason: Text


class Priority(Model):
    note_id: str = Field(
        description="Copy the id of a Note returned in strengths or issues, not an answer ID."
    )
    suggestion: Text


class AssessmentResult(Model):
    dimensions: Dimensions
    strengths: list[Note] = Field(max_length=8)
    issues: list[Note] = Field(max_length=12)
    retry_priority: Priority
    spoken_summary: str = Field(min_length=1, max_length=900)
    modeled_example: Text
    takeaway: Text


class Assessment(Model):
    status: Literal["none", "pending", "running", "ready", "unavailable"] = "none"
    request_id: str | None = None
    attempt_id: str | None = None
    frozen_hash: str | None = None
    deadline: float | None = None
    result: AssessmentResult | None = None
    error: str | None = None
    model: str = ""
    prompt_version: str = "assessment-v1"
    rubric_version: str = "wording-v1"


class Receipt(Model):
    command_id: str
    revision: int
    input_id: str | None = None
    answer_id: str | None = None


class Helper(Model):
    id: str = Field(default_factory=new_id)
    generation_id: str
    status: Literal["pending", "running", "ready", "unavailable"] = "pending"
    text: str | None = None
    deadline: float | None = None


class TargetedResult(Model):
    target_note_id: str
    status: Literal["demonstrated", "developing", "not_enough_detail", "transcript_unclear"]
    observation: Text
    evidence: list[Evidence] = Field(max_length=8)
    suggestion: Text
    modeled_example: Text


class TargetedAssessment(Model):
    status: Literal["none", "pending", "running", "ready", "unavailable"] = "none"
    request_id: str | None = None
    attempt_id: str | None = None
    frozen_hash: str | None = None
    deadline: float | None = None
    result: TargetedResult | None = None


class FocusedRetry(Model):
    id: str = Field(default_factory=new_id)
    target_note_id: str
    target: Text
    situation: str | None = None
    setup: str | None = None
    question_id: str | None = None
    answers: list[Answer] = Field(default_factory=list, max_length=2)
    assessment: TargetedAssessment = Field(default_factory=TargetedAssessment)


class CoachingReply(Model):
    text: str = Field(min_length=1, max_length=900)
    evidence: list[Evidence] = Field(max_length=8)


class CoachingTurn(Model):
    id: str = Field(default_factory=new_id)
    input_id: str
    transcript: Transcript
    reply: CoachingReply
    message_id: str


class Command(Model):
    command_id: Identifier
    expected_revision: int = Field(ge=1)
    connection_epoch: str | None = None
    type: Literal[
        "pause",
        "finish",
        "done",
        "use_answer",
        "try_again",
        "retry_operation",
        "mute",
        "unmute",
        "replay",
        "continue_answer",
        "hint",
        "focused_retry",
        "expression",
    ]
    input_id: str | None = None
    expression_id: Literal["expression", "alternative", "example"] | None = None
    target_note_id: str | None = None


class Session(Model):
    schema_version: int = 1
    id: str = Field(default_factory=new_id)
    guest_id: str
    purpose_id: str
    content_version: str
    conversation_model: str
    prompt_version: str = "conversation-v1"
    revision: int = 1
    sequence: int = 1
    lifecycle: Literal["in_progress", "paused", "completed"] = "paused"
    phase: Literal["roleplay", "coaching", "retry"] = "roleplay"
    substate: Literal[
        "connecting",
        "opening",
        "listening",
        "thinking",
        "speaking",
        "capped",
        "assessment_pending",
        "ready",
        "unavailable",
    ] = "connecting"
    created_at: float
    last_practice_at: float
    expires_at: float
    completed_at: float | None = None
    connection_epoch: str | None = None
    room: str | None = None
    participant: str | None = None
    generation_id: str = Field(default_factory=new_id)
    situation: str | None = None
    setup: str | None = None
    question_id: str | None = None
    answers: list[Answer] = Field(default_factory=list, max_length=3)
    messages: list[TutorMessage] = Field(default_factory=list, max_length=100)
    input: Input | None = None
    pending_command: Command | None = None
    receipts: dict[str, Receipt] = Field(default_factory=dict)
    assessment: Assessment = Field(default_factory=Assessment)
    notice: str | None = None
    capture_muted: bool = False
    replay_restore_capture: bool = False
    helper: Helper | None = None
    retries: list[FocusedRetry] = Field(default_factory=list, max_length=12)
    coaching_turns: list[CoachingTurn] = Field(default_factory=list, max_length=30)
    source_session_id: str | None = None
    previous_opening: str | None = None


class OpeningProposal(Model):
    situation: Text
    setup: Text
    prompt: str = Field(
        min_length=1,
        max_length=650,
        description="One direct question from Alex to the learner, ending in a question mark.",
    )

    @field_validator("setup")
    @classmethod
    def setup_is_not_a_question(cls, value):
        if "?" in value:
            raise ValueError("Keep the setup declarative; ask the only question in prompt.")
        return value

    @field_validator("prompt")
    @classmethod
    def opening_is_a_question(cls, value):
        value = value.strip()
        if not value.endswith("?") or value.count("?") != 1:
            raise ValueError("Ask exactly one direct question ending with a question mark.")
        return value


class FollowUp(Model):
    kind: Literal["follow_up"]
    acknowledgment: str = Field(max_length=350)
    question: str = Field(min_length=1, max_length=500)


class Close(Model):
    kind: Literal["coaching"]
    acknowledgment: str = Field(min_length=1, max_length=350)
    bridge: str = Field(min_length=1, max_length=350)


class Help(Model):
    kind: Literal["help"]
    text: str = Field(min_length=1, max_length=700)


class TurnProposal(Model):
    contribution_kind: Literal["answer", "help", "coaching_question", "unusable"]
    relation: Literal["new_answer", "continuation"]
    goal_demonstrated: bool
    action: Annotated[FollowUp | Close | Help, Field(discriminator="kind")]


class ContinuationProposal(TurnProposal):
    relation: Literal["continuation"]
