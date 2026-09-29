"""Billable, synthetic text fixtures through actual Inference; never learner recordings."""

import asyncio
import json
import os
import time

from livekit.agents.utils import http_context

from app.config import settings
from app.content import content
from app.conversation.context import OPENING_INSTRUCTIONS, TURN_INSTRUCTIONS, context, encode
from app.sessions.models import (
    Input,
    OpeningProposal,
    Session,
    Transcript,
    TurnProposal,
    TutorMessage,
    new_id,
)
from app.sessions.transitions import accept, validate_turn
from app.voice.inference import Inference

FIXTURES = [
    [
        "Good morning everyone. Thank you for joining. Let's discuss next week's project plan.",
        "I'd like us to agree on our priorities today. Alex, what would you add?",
    ],
    [
        "Today I'd like us to agree on our launch date and next steps.",
        "First let's review the timeline, then assign owners. Alex, what risks should we discuss?",
    ],
    [
        "Let's confirm our next steps. I'll send the plan today and Alex will review it tomorrow.",
        "We'll check progress on Friday. Thanks everyone for your time and ideas.",
    ],
    [
        "I've finished the first draft of the project timeline. Two dates still need checking.",
        "I'll check those dates with the team today and send you the updated version tomorrow.",
    ],
    [
        "I'm having trouble accessing the customer data. Could you help me get permission?",
        "I need the data by Thursday for my report. Would you be able to contact the data owner?",
    ],
    [
        "Could I get your feedback on the opening section of my report? "
        "I'd like to make it clearer.",
        "Thanks, that's helpful. I'll put the main finding first. "
        "Could you check the revised version tomorrow?",
    ],
    [
        "Hi Alex, how's your week going? I heard you're working on the new project.",
        "That sounds interesting. What's been the most enjoyable part so far?",
    ],
    [
        "You mentioned trying a new cafe. How was it?",
        "It sounds lovely. What would you recommend if I go there this weekend?",
    ],
    [
        "It was lovely catching up. I need to get back to my desk now.",
        "Thanks for the chat. Let's catch up again after the project review. See you later!",
    ],
]


async def main():
    config = settings()
    models = Inference(config)
    failures = []
    async with http_context.open():
        for selected, words in zip(content().purposes, FIXTURES, strict=True):
            only = os.environ.get("CHECK_PURPOSES")
            if only and selected.purpose_id not in only.split(","):
                continue
            now = time.time()
            session = Session(
                guest_id=new_id(),
                purpose_id=selected.purpose_id,
                content_version=content().version,
                conversation_model=config.conversation_model,
                created_at=now,
                last_practice_at=now,
                expires_at=now + 86400,
                lifecycle="in_progress",
            )
            try:
                opening = await models.structured(
                    OpeningProposal,
                    OPENING_INSTRUCTIONS,
                    encode(context(session)),
                    model=config.conversation_model,
                )
                session.situation, session.setup = opening.situation, opening.setup
                first = TutorMessage(
                    generation_id=session.generation_id,
                    kind="opening",
                    text=f"{opening.setup} {opening.prompt}",
                    delivery="completed",
                )
                session.messages.append(first)
                session.question_id = first.id
                for utterance in words + [words[-1]]:
                    session.input = Input(status="submitting", capture_seconds=8)

                    def valid(value, session=session):
                        try:
                            validate_turn(session, value)
                        except Exception as error:
                            raise ValueError(str(error)) from None

                    turn = await models.structured(
                        TurnProposal,
                        TURN_INSTRUCTIONS,
                        encode(
                            {
                                **context(session),
                                "current_transcript": utterance,
                                "current_transcript_status": "reliable",
                                "current_answer_number_if_accepted": len(session.answers) + 1,
                                "permitted_relation": "new_answer",
                            }
                        ),
                        model=config.conversation_model,
                        validate=valid,
                    )
                    accept(
                        session,
                        session.input.id,
                        Transcript(text=utterance, source_identity="synthetic"),
                        turn,
                        time.time(),
                        86400,
                    )
                    if session.phase == "coaching":
                        break
                assert session.phase == "coaching" and 2 <= len(session.answers) <= 3
                print(
                    json.dumps(
                        {
                            "purpose": selected.purpose_id,
                            "passed": True,
                            "accepted_answers": len(session.answers),
                            "opening": first.text,
                        }
                    ),
                    flush=True,
                )
            except Exception as error:
                failures.append(selected.purpose_id)
                print(
                    json.dumps(
                        {
                            "purpose": selected.purpose_id,
                            "passed": False,
                            "error": type(error).__name__,
                            "detail": str(error),
                        }
                    ),
                    flush=True,
                )
    if failures:
        raise SystemExit(1)


asyncio.run(main())
