import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from livekit import rtc

from app.voice.inference import Inference


def delayed_provider(models, *, failure=False):
    waiting, release = asyncio.Event(), asyncio.Event()
    frame = rtc.AudioFrame.create(24000, 1, 480)

    async def chunks():
        yield SimpleNamespace(frame=frame)
        waiting.set()
        await release.wait()
        if failure:
            raise TimeoutError("fixture delivery failure")
        yield SimpleNamespace(frame=frame)

    # Async iteration special methods must live on the type.
    class Stream:
        def __init__(self):
            self.iterator = chunks()

        def push_text(self, text):
            pass

        def end_input(self):
            pass

        def __aiter__(self):
            return self

        async def __anext__(self):
            return await anext(self.iterator)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.iterator.aclose()

    client = SimpleNamespace(stream=Mock(side_effect=lambda **_: Stream()), aclose=AsyncMock())
    models.tts = Mock(return_value=client)
    return waiting, release, client


@pytest.mark.parametrize("outcome", ["success", "failure", "cancel"])
async def test_speech_prepares_complete_audio_before_playing(config, outcome):
    models = Inference(config)
    waiting, release, client = delayed_provider(models, failure=outcome == "failure")
    emitted = []

    async def play():
        async for frame in models.speech("Could you get us started?"):
            emitted.append(frame)

    task = asyncio.create_task(play())
    try:
        await asyncio.wait_for(waiting.wait(), 2)
        # The first chunk would be exhausted while the next chunk is still missing.
        assert emitted == []
        if outcome == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            release.set()
            if outcome == "failure":
                with pytest.raises(TimeoutError):
                    await task
                assert emitted == []
            else:
                await task
                assert len(emitted) == 2
        client.aclose.assert_awaited_once()
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
