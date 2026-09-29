"""Only the current answer's mono 16 kHz PCM16 lives here, never on disk."""

import time
from dataclasses import dataclass, field


@dataclass
class AnswerBuffer:
    input_id: str
    limit_seconds: float = 120
    started: float | None = None
    pcm: bytearray = field(default_factory=bytearray)
    segment_ids: list[str] = field(default_factory=list)
    final_segments: list[str] = field(default_factory=list)
    sealed: bool = False
    text: str | None = None

    def speech(self, now: float | None = None):
        if self.started is None:
            self.started = time.monotonic() if now is None else now

    def duration(self, now: float | None = None) -> float:
        if self.started is None:
            return 0
        return min(
            self.limit_seconds, max(0, (time.monotonic() if now is None else now) - self.started)
        )

    def append(self, frame):
        if self.sealed or self.started is None:
            return
        if frame.sample_rate != 16000 or frame.num_channels != 1:
            raise ValueError("Unexpected capture format")
        # 3.84 MiB PCM plus copies stays within the 8 MiB application budget.
        data = frame.data.cast("B")
        if len(self.pcm) + len(data) > 3_840_000:
            raise BufferError("capture_memory_limit")
        self.pcm.extend(data)

    def clear(self):
        self.pcm.clear()
        self.segment_ids.clear()
        self.final_segments.clear()
        self.text = None
        self.sealed = True

    def transcript_status(self):
        # The SDK can return an interim tail after its final-transcript timeout.
        # Preserve that uncertainty; availability must not be inferred from word count.
        finalized = " ".join(" ".join(self.final_segments).split())
        submitted = " ".join((self.text or "").split())
        return "reliable" if submitted and submitted == finalized else "unclear"
