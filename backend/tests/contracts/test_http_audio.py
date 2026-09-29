import pytest
from livekit import rtc

from app.voice.http_audio import response


@pytest.mark.parametrize("failure", [False, True])
async def test_stream_marks_completion_or_provider_failure(config, monkeypatch, failure):
    async def speech(self, text):
        yield rtc.AudioFrame.create(24000, 1, 480)
        if failure:
            raise TimeoutError("synthetic provider timeout")

    monkeypatch.setattr("app.voice.http_audio.Inference.speech", speech)
    stream = response(config, "Synthetic phrase")
    chunks = [chunk async for chunk in stream.body_iterator]
    assert int.from_bytes(chunks[0][:4], "big") == 960
    assert chunks[-1] == (0xFFFFFFFF if failure else 0).to_bytes(4, "big")
    assert stream.headers["X-Audio-Framing"] == "length-prefix-v1"
