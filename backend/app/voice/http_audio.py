"""Framed streaming PCM distinguishes successful completion from upstream truncation."""

import asyncio

from fastapi.responses import StreamingResponse
from livekit.agents.utils import http_context

from app.voice.inference import Inference


def response(config, text, authorize=None):
    async def audio():
        try:
            async with asyncio.timeout(90), http_context.open():
                async for frame in Inference(config).speech(text):
                    if authorize:
                        await authorize()
                    pcm = bytes(frame.data)
                    yield len(pcm).to_bytes(4, "big") + pcm
                if authorize:
                    await authorize()
                yield bytes(4)  # Explicit successful end; EOF alone is never success.
        except asyncio.CancelledError:
            raise
        except Exception:
            yield (0xFFFFFFFF).to_bytes(4, "big")

    return StreamingResponse(
        audio(),
        media_type="application/octet-stream",
        headers={
            "X-Audio-Sample-Rate": "24000",
            "X-Audio-Channels": "1",
            "X-Audio-Framing": "length-prefix-v1",
            "X-Accel-Buffering": "no",
        },
    )
