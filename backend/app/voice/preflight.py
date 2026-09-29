"""Billable, non-personal fixtures, generated audio in RAM only."""

import asyncio
import json
import time

from livekit import rtc
from livekit.agents import stt
from livekit.agents.utils import http_context

from app.assessment.context import INSTRUCTIONS, assessment_context
from app.assessment.validation import validate_result
from app.config import settings
from app.conversation.context import OPENING_INSTRUCTIONS, context, encode
from app.observability import configure_logs
from app.sessions.models import (
    Answer,
    AssessmentResult,
    OpeningProposal,
    Session,
    Transcript,
    new_id,
)
from app.voice.inference import Inference, ProviderUnavailable


async def run_checks():
    configure_logs()
    config = settings()
    models = Inference(config)
    now = time.time()
    saved = Session(
        guest_id=new_id(),
        purpose_id="welcome-everyone",
        content_version="preflight",
        conversation_model=config.conversation_model,
        created_at=now,
        last_practice_at=now,
        expires_at=now + 60,
    )
    results = {}

    async def check(role, operation):
        started = time.monotonic()
        try:
            value = await asyncio.wait_for(operation(), 60)
            results[role] = {
                "status": "passed",
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
            return value
        except Exception as error:
            results[role] = {
                "status": "unavailable",
                "error_type": type(error).__name__,
                "error_category": str(error) if isinstance(error, ProviderUnavailable) else None,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
            return None

    async def conversation():
        return await models.structured(
            OpeningProposal,
            OPENING_INSTRUCTIONS,
            encode(context(saved)),
            model=config.conversation_model,
        )

    opening = await check("conversation", conversation)
    if opening:
        saved.situation, saved.setup = opening.situation, opening.setup

    fixture = "Good morning everyone. Thanks for making the time. Let's agree on our next steps."
    audio_frames = []

    async def tts_call():
        async for frame in models.speech(fixture):
            audio_frames.append(frame)
        if not audio_frames:
            raise ValueError("No audio")

    await check("tts", tts_call)

    async def stt_call():
        client = models.stt()
        texts = []
        final = asyncio.Event()
        try:
            async with client.stream() as stream:

                async def send():
                    for frame in audio_frames:
                        stream.push_frame(frame)
                        await asyncio.sleep(frame.samples_per_channel / frame.sample_rate)
                    # A non-personal, in-memory silent tail gives STT an endpoint to finalize.
                    rate = audio_frames[0].sample_rate
                    stream.push_frame(rtc.AudioFrame(bytes(rate * 2), rate, 1, rate))
                    stream.end_input()

                async def receive():
                    async for event in stream:
                        if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                            texts.extend(alt.text for alt in event.alternatives[:1])
                            final.set()

                receiver = asyncio.create_task(receive())
                try:
                    await send()
                    await asyncio.wait_for(final.wait(), 10)
                finally:
                    receiver.cancel()
                    await asyncio.gather(receiver, return_exceptions=True)
            if not " ".join(texts).strip():
                raise ValueError("No final transcript")
        finally:
            await client.aclose()
            audio_frames.clear()

    await check("stt", stt_call)

    for text in (
        fixture,
        "By the end of the meeting, I'd like us to agree on the owners and deadlines.",
    ):
        saved.answers.append(
            Answer(
                input_id=new_id(),
                question_id=new_id(),
                capture_seconds=6,
                transcript=Transcript(text=text, source_identity="preflight-fixture"),
            )
        )

    async def assessment():
        return await models.structured(
            AssessmentResult,
            INSTRUCTIONS,
            encode(assessment_context(saved)),
            model=config.assessment_model,
            timeout=config.assessment_timeout_seconds,
            validate=lambda result: validate_result(saved, result),
        )

    await check("assessment", assessment)
    print(json.dumps({"billable_fixture_calls": True, "results": results}, indent=2))
    if any(result["status"] != "passed" for result in results.values()):
        raise SystemExit(1)


async def main():
    async with http_context.open():
        await run_checks()


if __name__ == "__main__":
    asyncio.run(main())
