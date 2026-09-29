import { expect, test } from "vitest";
import { PcmFrames } from "../../src/voice/pcm";

test("PCM framing survives every split point and requires explicit completion", () => {
  const wire = new Uint8Array([0, 0, 0, 4, 1, 2, 3, 4, 0, 0, 0, 0]);
  for (let split = 0; split <= wire.length; split++) {
    const decoder = new PcmFrames();
    const frames = [
      ...decoder.push(wire.slice(0, split)),
      ...decoder.push(wire.slice(split)),
    ];
    expect(frames.map((f) => [...f])).toEqual([[1, 2, 3, 4]]);
    expect(() => decoder.finish()).not.toThrow();
  }
  const incomplete = new PcmFrames();
  incomplete.push(wire.slice(0, 8));
  expect(() => incomplete.finish()).toThrow("audio_incomplete");
  expect(() => incomplete.push(new Uint8Array([255, 255, 255, 255]))).toThrow(
    "playback_unavailable",
  );
});
