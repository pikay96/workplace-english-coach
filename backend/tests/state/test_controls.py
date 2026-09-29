import pytest

from app.sessions.models import Command, Input, new_id
from app.sessions.transitions import Rejected, command
from app.voice.buffer import AnswerBuffer


def test_mute_discards_cap_but_preserves_alex_playback(session):
    from app.sessions.models import TutorMessage

    session.lifecycle = "in_progress"
    output = TutorMessage(
        generation_id=session.generation_id,
        text="Alex speaking",
        kind="follow_up",
        delivery="playing",
    )
    session.messages.append(output)

    def mute():
        command(
            session,
            Command(command_id=new_id(), expected_revision=1, type="mute"),
            session.created_at,
            86400,
        )

    mute()
    assert session.capture_muted and output.delivery == "playing"
    session.input = Input(status="awaiting_limit_confirmation", first_speech_at=session.created_at)
    output.delivery = "completed"
    mute()
    assert session.input is None and session.answers == []
    assert "discarded" in session.notice


def test_continuation_interval_uses_remaining_clock():
    buffer = AnswerBuffer(new_id(), limit_seconds=12)
    buffer.speech(100)
    assert buffer.duration(105) == 5
    assert buffer.duration(115) == 12


def test_pause_discards_cap_and_does_not_renew_retention(session):
    session.lifecycle = "in_progress"
    session.connection_epoch = new_id()
    session.input = Input(status="awaiting_limit_confirmation")
    expiry, generation = session.expires_at, session.generation_id
    value = Command(
        command_id=new_id(),
        expected_revision=1,
        type="pause",
        connection_epoch=session.connection_epoch,
    )
    command(session, value, session.created_at + 20, 86400)
    assert session.input is None and session.lifecycle == "paused"
    assert session.expires_at == expiry and session.generation_id != generation
    receipt = command(session, value, session.created_at + 40, 86400)
    assert receipt.command_id == value.command_id and session.expires_at == expiry


def test_cap_requires_explicit_choice_and_keeps_input_identity(session):
    session.lifecycle = "in_progress"
    session.connection_epoch = new_id()
    session.input = Input(status="awaiting_limit_confirmation")
    input_id = session.input.id

    def cmd(kind):
        return Command(
            command_id=new_id(),
            expected_revision=1,
            type=kind,
            input_id=input_id,
            connection_epoch=session.connection_epoch,
        )

    with pytest.raises(Rejected):
        command(session, cmd("done"), session.created_at, 86400)
    command(session, cmd("use_answer"), session.created_at, 86400)
    assert session.input.id == input_id and session.input.status == "submitting"
    assert session.answers == []


def test_capture_timer_starts_on_first_speech_and_includes_pauses():
    buffer = AnswerBuffer(new_id())
    assert buffer.duration(500) == 0
    buffer.speech(500)
    buffer.speech(540)
    assert buffer.duration(560) == 60
    assert buffer.duration(625) == 120
    buffer.pcm.extend(b"test")
    buffer.clear()
    assert not buffer.pcm and buffer.sealed
