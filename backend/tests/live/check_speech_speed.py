"""Compare real TTS at the default rate and the configured learner rate.

Billable: synthesizes fixed, non-personal text twice. Stores no audio.
Run from the repository root:
Get-Content backend/tests/live/check_speech_speed.py | docker compose exec -T api python -
"""

import asyncio
import json

from livekit.agents.utils import http_context

from app.config import settings
from app.observability import configure_logs
from app.voice.inference import Inference

PHRASE = (
    "Good to see you. Let's practice opening a meeting. "
    "Take your time, and use your own words. How would you welcome your colleagues?"
)


async def main():
    configure_logs()
    config = settings()
    results = []
    async with http_context.open():
        for speed in (1.0, config.tts_speed):
            duration = 0.0
            error_type = None
            try:
                async with asyncio.timeout(65):
                    async for frame in Inference(
                        config.model_copy(update={"tts_speed": speed})
                    ).speech(PHRASE):
                        duration += frame.samples_per_channel / frame.sample_rate
            except Exception as error:
                error_type = type(error).__name__
            result = {
                "speed": speed,
                "audio_seconds": round(duration, 3),
                "error_type": error_type,
            }
            results.append(result)
            print(json.dumps(result), flush=True)
    passed = (
        all(r["error_type"] is None for r in results)
        and results[0]["audio_seconds"] > 0
        and results[1]["audio_seconds"] > results[0]["audio_seconds"] * 1.1
    )
    print(json.dumps({"slower_speech_verified": passed}), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
