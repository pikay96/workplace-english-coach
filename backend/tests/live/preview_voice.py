"""Billable voice audition using synthetic text; writes only the requested preview.

Run inside the API container, then copy /tmp/alex-voice-preview.wav out to listen.
This uses the configured application TTS, speed, and complete-reply buffering.
It is a listening sample, not an automated judgment of pronunciation quality.
"""

import asyncio
import json
import wave

from livekit.agents.utils import http_context

from app.config import settings
from app.observability import configure_logs
from app.voice.inference import Inference

PHRASE = (
    "Good morning. Everyone is here and ready for the meeting. "
    "Could you get us started? "
    "The goal today is to agree on our next steps. "
    "Before we finish, let's confirm who is doing what."
)


async def main():
    configure_logs()
    config = settings()
    pcm = bytearray()
    async with http_context.open(), asyncio.timeout(65):
        async for frame in Inference(config).speech(PHRASE):
            pcm.extend(frame.data)
    if not pcm:
        raise RuntimeError("empty_preview")
    path = "/tmp/alex-voice-preview.wav"
    with wave.open(path, "wb") as sample:
        sample.setnchannels(1)
        sample.setsampwidth(2)
        sample.setframerate(24000)
        sample.writeframes(pcm)
    print(
        json.dumps(
            {
                "path": path,
                "voice": config.tts_voice,
                "speed": config.tts_speed,
                "audio_seconds": round(len(pcm) / 48000, 3),
                "text": PHRASE,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
