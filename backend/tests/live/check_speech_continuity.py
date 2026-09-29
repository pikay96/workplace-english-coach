"""Billable TTS-only diagnostic. Fixed non-personal text; no audio is retained.

From the repository root in PowerShell:
Get-Content backend/tests/live/check_speech_continuity.py |
    docker compose exec -T api python -

Exits nonzero when application audio delivery would starve an immediately
started player for more than 500 ms. The application now buffers the complete
synthesis, so first_frame_ms includes preparation. This does not measure raw
provider chunk timing, encoded silence, browser output, or latency percentiles.
"""

import asyncio
import json
import time

from livekit.agents.utils import http_context

from app.config import settings
from app.observability import configure_logs
from app.voice.inference import Inference

FIXTURE = "Good morning everyone. Thanks for making the time. Let's agree on our next steps."


async def main():
    configure_logs()
    started = time.monotonic()
    available_until = None
    first_frame_ms = None
    audio_seconds = 0.0
    max_gap_seconds = 0.0
    gap_count = 0
    error_type = None

    try:
        async with http_context.open(), asyncio.timeout(65):
            async for frame in Inference(settings()).speech(FIXTURE):
                now = time.monotonic()
                if available_until is None:
                    first_frame_ms = round((now - started) * 1000)
                    available_until = now
                gap = max(0.0, now - available_until)
                max_gap_seconds = max(max_gap_seconds, gap)
                gap_count += int(gap > 0.5)
                duration = frame.samples_per_channel / frame.sample_rate
                available_until = max(now, available_until) + duration
                audio_seconds += duration
    except Exception as error:
        # Provider exception bodies may contain payloads. Only expose the type.
        error_type = type(error).__name__

    passed = error_type is None and audio_seconds > 0 and max_gap_seconds <= 0.5
    print(
        json.dumps(
            {
                "billable_fixture_call": True,
                "passed": passed,
                "first_frame_ms": first_frame_ms,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "audio_seconds": round(audio_seconds, 3),
                "max_delivery_gap_ms": round(max_gap_seconds * 1000),
                "delivery_gaps_over_500ms": gap_count,
                "error_type": error_type,
            },
            indent=2,
        ),
        flush=True,
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
