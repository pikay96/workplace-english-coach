"""Generate non-personal fixture speech into stdout JSON, never a learner recording."""

import asyncio
import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents.utils import http_context

from app.config import settings
from app.observability import configure_logs
from app.voice.inference import Inference

PHRASES = {
    "coaching_question": "Could you explain why that wording sounds more natural?",
    "welcome": (
        "Good morning, everyone. Thank you for joining our meeting today. "
        "I'm Sam and I'll be hosting. Before we begin, let's quickly introduce ourselves."
    ),
    "goal": (
        "Welcome, everyone. I appreciate you making the time. Today we'll agree on owners "
        "and deadlines, so let's get started with a quick round of introductions."
    ),
    "brief": "The update is ready. I have sent the files. The report has the details.",
    "agenda": (
        "The report covers June and July. The numbers are in the spreadsheet, "
        "and the chart shows the totals for both months."
    ),
    "long_answer": Path(__file__).with_name("long_answer.txt").read_text(encoding="utf-8"),
}


async def main():
    load_dotenv("../.env")
    configure_logs()
    models = Inference(settings())
    result = {}
    capacity = asyncio.Semaphore(2)

    async def generate(name, text):
        async with capacity:
            pcm = bytearray()
            try:
                async with asyncio.timeout(90):
                    async for frame in models.speech(text):
                        pcm.extend(frame.data.cast("B"))
                result[name] = base64.b64encode(pcm).decode()
            finally:
                pcm.clear()

    async with http_context.open():
        await asyncio.gather(*(generate(name, text) for name, text in PHRASES.items()))
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
