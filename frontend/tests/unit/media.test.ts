import { beforeEach, expect, test, vi } from "vitest";
import type { Connection, Session } from "../../src/api/client";
import { MediaController } from "../../src/voice/controller";

test.each(["request", "stream"])(
  "stopping Review during %s is not a playback error",
  async (stage) => {
    vi.stubGlobal(
      "AudioContext",
      class {
        currentTime = 0;
        async resume() {}
      },
    );
    vi.stubGlobal(
      "fetch",
      vi.fn((_url, { signal }: RequestInit) => {
        if (stage === "request")
          return new Promise((_resolve, reject) => {
            signal!.addEventListener("abort", () =>
              reject(new DOMException("Stopped", "AbortError")),
            );
          });
        return Promise.resolve(
          new Response(
            new ReadableStream({
              start(controller) {
                signal!.addEventListener("abort", () =>
                  controller.error(new DOMException("Stopped", "AbortError")),
                );
              },
            }),
          ),
        );
      }),
    );
    try {
      const controller = new MediaController();
      const playback = controller.review("fixture", "takeaway");
      const settled = expect(playback).resolves.toBeUndefined();
      await Promise.resolve();
      controller.stop();
      await settled;
    } finally {
      vi.unstubAllGlobals();
    }
  },
);

const mocks = vi.hoisted(() => ({
  track: {
    mediaStreamTrack: { enabled: true, stop: vi.fn() },
    mute: vi.fn(async () => {}),
    unmute: vi.fn(async () => {}),
    stop: vi.fn(),
  },
  create: vi.fn(),
  publish: vi.fn(async () => {}),
}));
vi.mock("livekit-client", () => ({
  createLocalAudioTrack: mocks.create,
  Room: class {
    localParticipant = { publishTrack: mocks.publish };
    on() {}
    async connect() {}
    async startAudio() {}
    async disconnect() {}
  },
  RoomEvent: {
    TrackSubscribed: "track",
    Reconnecting: "reconnecting",
    Disconnected: "disconnected",
  },
  Track: { Kind: { Audio: "audio" }, Source: { Microphone: "microphone" } },
}));

beforeEach(() => vi.clearAllMocks());

test.each(["success", "failure"])(
  "HTTP playback waits for the complete audio before %s",
  async (outcome) => {
    let stream!: ReadableStreamDefaultController<Uint8Array>;
    const start = vi.fn();
    vi.stubGlobal(
      "AudioContext",
      class {
        currentTime = 0;
        destination = {};
        async resume() {}
        createBuffer(_channels: number, length: number, rate: number) {
          return {
            duration: length / rate,
            getChannelData: () => new Float32Array(length),
          };
        }
        createBufferSource() {
          return {
            connect() {},
            disconnect() {},
            stop() {},
            onended: () => {},
            start() {
              start();
              queueMicrotask(() => this.onended());
            },
          };
        }
      },
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            new ReadableStream({
              start(controller) {
                stream = controller;
              },
            }),
            { headers: { "X-Audio-Framing": "length-prefix-v1" } },
          ),
      ),
    );
    const controller = new MediaController();
    try {
      const playback = controller.expression("welcome-everyone", "expression");
      const finished =
        outcome === "failure"
          ? expect(playback).rejects.toThrow("playback_unavailable")
          : expect(playback).resolves.toBeUndefined();
      await vi.waitFor(() => expect(stream).toBeDefined());
      stream.enqueue(new Uint8Array([0, 0, 0, 2, 1, 0]));
      await new Promise((resolve) => setTimeout(resolve, 20));
      expect(start).not.toHaveBeenCalled();
      stream.enqueue(
        outcome === "failure"
          ? new Uint8Array([255, 255, 255, 255])
          : new Uint8Array([0, 0, 0, 2, 2, 0, 0, 0, 0, 0]),
      );
      stream.close();
      await finished;
      expect(start).toHaveBeenCalledTimes(outcome === "success" ? 1 : 0);
    } finally {
      controller.stop();
      vi.unstubAllGlobals();
    }
  },
);

test("an early snapshot cannot prevent capture after microphone initialization", async () => {
  let ready!: (track: typeof mocks.track) => void;
  mocks.create.mockImplementation(
    () =>
      new Promise((resolve) => {
        ready = resolve;
      }),
  );
  const controller = new MediaController();
  const saved = {
    connection_epoch: "epoch",
    lifecycle: "in_progress",
    substate: "listening",
    input: { status: "open" },
    messages: [],
  } as unknown as Session;
  const connecting = controller.connect({
    url: "wss://fixture",
    token: "fixture",
    session: saved,
  } as Connection);
  await vi.waitFor(() => expect(mocks.create).toHaveBeenCalled());
  controller.sync(saved);
  expect(mocks.track.unmute).not.toHaveBeenCalled();
  ready(mocks.track);
  await connecting;
  expect(mocks.track.mute.mock.invocationCallOrder[0]).toBeLessThan(
    mocks.publish.mock.invocationCallOrder[0],
  );
  controller.sync(saved);
  expect(mocks.track.unmute).toHaveBeenCalledTimes(1);
  controller.stop();
  expect(mocks.track.stop).toHaveBeenCalledOnce();
});

test("microphone stays muted during Alex playback and opens only for Your turn", async () => {
  mocks.create.mockResolvedValue(mocks.track);
  const controller = new MediaController();
  const saved = {
    connection_epoch: "epoch",
    lifecycle: "in_progress",
    substate: "speaking",
    // Also fail closed for an old snapshot retaining an input during playback.
    input: { status: "open" },
    messages: [{ delivery: "playing", playback_id: "playback" }],
  } as unknown as Session;
  await controller.connect({
    url: "wss://fixture",
    token: "fixture",
    session: saved,
  } as Connection);
  controller.sync(saved);
  expect(mocks.track.unmute).not.toHaveBeenCalled();
  controller.suspendCapture(false, true);
  expect(mocks.track.mediaStreamTrack.stop).toHaveBeenCalledOnce();
  expect(mocks.track.mediaStreamTrack.enabled).toBe(false);
  controller.releaseHold();
  saved.substate = "listening";
  controller.sync(saved);
  expect(mocks.track.unmute).not.toHaveBeenCalled();
  saved.messages[0].delivery = "completed";
  controller.sync(saved);
  expect(mocks.track.unmute).toHaveBeenCalledOnce();
  saved.substate = "thinking";
  controller.sync(saved);
  expect(mocks.track.mute).toHaveBeenCalledTimes(3);
  controller.stop();
});
