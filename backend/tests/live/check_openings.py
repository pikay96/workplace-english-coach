"""Billable opening-only checks for all purposes; synthetic sessions, no persistence."""

import asyncio
import json
import time

from livekit.agents.utils import http_context

from app.config import settings
from app.content import content
from app.conversation.context import OPENING_INSTRUCTIONS, context, encode, validate_opening
from app.sessions.models import FocusedRetry, OpeningProposal, Session, new_id
from app.voice.inference import Inference


async def main():
    config = settings()
    models = Inference(config)
    failures = 0
    async with http_context.open():
        for selected in content().purposes:
            now = time.time()
            session = Session(
                guest_id=new_id(),
                purpose_id=selected.purpose_id,
                content_version=content().version,
                conversation_model=config.conversation_model,
                created_at=now,
                last_practice_at=now,
                expires_at=now + 86400,
            )
            phases = ["roleplay", "retry"] if selected.order in (0, 6, 7) else ["roleplay"]
            for phase in phases:
                if phase == "retry":
                    session.phase = "retry"
                    session.retries.append(
                        FocusedRetry(
                            target_note_id="synthetic",
                            target=selected.communication_goal,
                        )
                    )
                try:
                    opening = await models.structured(
                        OpeningProposal,
                        OPENING_INSTRUCTIONS,
                        encode(context(session)),
                        model=config.conversation_model,
                        validate=lambda value, session=session: validate_opening(session, value),
                    )
                    text = f"{opening.setup} {opening.prompt}"
                    passed = text.endswith("?") and text.count("?") == 1
                    session.previous_opening = text
                    session.situation, session.setup = opening.situation, opening.setup
                    print(
                        json.dumps(
                            {
                                "purpose": selected.purpose_id,
                                "phase": phase,
                                "passed": passed,
                                "opening": text,
                            }
                        ),
                        flush=True,
                    )
                    failures += int(not passed)
                except Exception as error:
                    failures += 1
                    print(
                        json.dumps(
                            {
                                "purpose": selected.purpose_id,
                                "phase": phase,
                                "passed": False,
                                "error_type": type(error).__name__,
                            }
                        ),
                        flush=True,
                    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
