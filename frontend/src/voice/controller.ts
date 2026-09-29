import { createLocalAudioTrack, Room, RoomEvent, Track } from "livekit-client";
import type { LocalAudioTrack, RemoteAudioTrack } from "livekit-client";
import type { Connection, Session } from "../api/client";
import { TabOwnership } from "./tabs";
import { PcmFrames } from "./pcm";

/** Owns every capture/playback resource. Stop invalidates pending async work immediately. */
export class MediaController {
  private generation = 0;
  private room?: Room;
  private mic?: LocalAudioTrack;
  private remote = new Set<RemoteAudioTrack>();
  private elements = new Map<RemoteAudioTrack, HTMLMediaElement>();
  private audio?: AudioContext;
  private sources = new Set<AudioBufferSourceNode>();
  private request?: AbortController;
  private playback?: string;
  private epoch?: string;
  private captureAllowed = false;
  private captureHold = false;
  private outputHold = false;
  private tabs = new TabOwnership(() => {
    this.stop();
    this.onLoss();
  });
  onLoss = () => {};
  onAudioError = () => {};

  unlock() {
    this.audio ??= new AudioContext();
    void this.audio.resume();
  }

  async connect(connection: Connection) {
    this.stop();
    const generation = this.generation;
    await this.tabs.acquire();
    if (generation !== this.generation) return;
    this.epoch = connection.session.connection_epoch ?? undefined;
    const room = new Room({ adaptiveStream: false, dynacast: false });
    this.room = room;
    room.on(RoomEvent.TrackSubscribed, (track) => {
      if (generation !== this.generation || track.kind !== Track.Kind.Audio)
        return;
      this.remote.add(track as RemoteAudioTrack);
      this.attach();
    });
    room.on(RoomEvent.Reconnecting, () => this.failClosed(generation));
    room.on(RoomEvent.Disconnected, () => this.failClosed(generation));
    try {
      await room.connect(connection.url, connection.token);
      if (generation !== this.generation) {
        await room.disconnect();
        return;
      }
      await room.startAudio();
      // Server has confirmed the old owner was fenced and the new room authorized.
      const track = await createLocalAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      });
      if (generation !== this.generation) {
        track.stop();
        return;
      }
      this.mic = track;
      await track.mute();
      await room.localParticipant.publishTrack(track, {
        source: Track.Source.Microphone,
      });
      if (generation !== this.generation) {
        track.stop();
        return;
      }
      // Input is opened by the next canonical snapshot, after the agent is ready.
    } catch (error) {
      this.stop();
      throw error;
    }
  }

  sync(saved: Session) {
    if (!this.room || saved.connection_epoch !== this.epoch) return;
    if (saved.lifecycle !== "in_progress") {
      this.stop();
      return;
    }
    const current = saved.messages.findLast((m) => m.delivery === "playing");
    const capture =
      saved.substate === "listening" &&
      saved.input?.status === "open" &&
      !saved.capture_muted &&
      !this.captureHold &&
      !current;
    if (this.mic && capture !== this.captureAllowed) {
      this.captureAllowed = capture;
      const mic = this.mic;
      if (capture)
        void mic
          .unmute()
          .then(() => {
            if (!this.captureAllowed || this.mic !== mic) {
              mic.mediaStreamTrack.enabled = false;
              mic.mediaStreamTrack.stop();
              return mic.mute();
            }
          })
          .catch(this.onAudioError);
      else {
        mic.mediaStreamTrack.enabled = false;
        void mic.mute().catch(this.onAudioError);
      }
    }
    const next = current?.playback_id ?? undefined;
    if (next !== this.playback) {
      this.detach();
      this.playback = next;
    }
    this.attach();
  }

  private attach() {
    if (!this.playback || this.outputHold) return;
    for (const track of this.remote) {
      if (this.elements.has(track)) continue;
      const element = track.attach();
      element.autoplay = true;
      element.setAttribute("playsinline", "");
      this.elements.set(track, element);
      void element.play().catch(this.onAudioError);
    }
  }

  private detach() {
    for (const [track, element] of this.elements) {
      element.pause();
      track.detach(element);
      element.srcObject = null;
      element.remove();
    }
    this.elements.clear();
  }

  private failClosed(generation: number) {
    if (generation !== this.generation) return;
    this.stop();
    this.onLoss();
  }

  stop() {
    this.generation++;
    this.tabs.release();
    this.captureHold = this.outputHold = false;
    this.captureAllowed = false;
    this.playback = undefined;
    this.mic?.stop();
    this.mic = undefined;
    this.detach();
    this.remote.clear();
    const room = this.room;
    this.room = undefined;
    if (room) void room.disconnect(true);
    this.request?.abort();
    this.request = undefined;
    for (const source of this.sources) {
      source.stop();
      source.disconnect();
    }
    this.sources.clear();
  }

  suspendCapture(stopOutput = false, stopDevice = false) {
    this.captureHold = true;
    this.captureAllowed = false;
    if (this.mic) {
      this.mic.mediaStreamTrack.enabled = false;
      // Explicit Mute releases the device. The pinned SDK reacquires an ended
      // managed microphone track on the next authorized unmute.
      if (stopDevice) this.mic.mediaStreamTrack.stop();
      void this.mic.mute().catch(this.onAudioError);
    }
    if (stopOutput) {
      this.outputHold = true;
      this.detach();
    }
  }

  releaseHold() {
    this.captureHold = this.outputHold = false;
  }

  async review(sessionId: string, messageId: string) {
    return this.playHttp(`/api/sessions/${sessionId}/playback`, {
      message_id: messageId,
    });
  }

  async expression(purposeId: string, expressionId: string) {
    return this.playHttp(`/api/content/${purposeId}/playback`, {
      expression_id: expressionId,
    });
  }

  private async playHttp(path: string, body: object) {
    this.stop();
    this.unlock();
    const generation = this.generation;
    await this.tabs.acquire();
    if (generation !== this.generation) return;
    const audio = this.audio!;
    const request = new AbortController();
    this.request = request;
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: request.signal,
        cache: "no-store",
      });
      if (!response.ok || !response.body)
        throw new Error("playback_unavailable");
      const rate = Number(response.headers.get("X-Audio-Sample-Rate") ?? 24000);
      const reader = response.body.getReader();
      const packets: Uint8Array[] = [];
      let byteLength = 0;
      const framed =
        response.headers.get("X-Audio-Framing") === "length-prefix-v1";
      const decoder = new PcmFrames();
      try {
        while (generation === this.generation) {
          const { value, done } = await reader.read();
          if (done) {
            if (framed) decoder.finish();
            break;
          }
          for (const packet of framed ? decoder.push(value) : [value]) {
            byteLength += packet.length;
            // Match the server's ninety-second PCM16 memory bound.
            if (byteLength > 24000 * 2 * 90) throw new Error("audio_too_large");
            packets.push(packet);
          }
        }
      } finally {
        await reader.cancel().catch(() => {});
      }
      if (generation !== this.generation) return;
      if (!byteLength || byteLength % 2) throw new Error("audio_incomplete");
      // Start only after a clean completion. One buffer cannot starve between
      // network chunks, and Stop still owns and cancels the source immediately.
      const bytes = new Uint8Array(byteLength);
      let offset = 0;
      for (const packet of packets) {
        bytes.set(packet, offset);
        offset += packet.length;
      }
      packets.length = 0;
      const buffer = audio.createBuffer(1, byteLength / 2, rate);
      const channel = buffer.getChannelData(0);
      const view = new DataView(bytes.buffer);
      for (let i = 0; i < channel.length; i++)
        channel[i] = view.getInt16(i * 2, true) / 32768;
      const source = audio.createBufferSource();
      source.buffer = buffer;
      source.connect(audio.destination);
      source.onended = () => {
        this.sources.delete(source);
        source.disconnect();
      };
      this.sources.add(source);
      source.start();
      while (generation === this.generation && this.sources.size)
        await new Promise((resolve) => setTimeout(resolve, 50));
      if (generation === this.generation) this.tabs.release();
    } catch (error) {
      // Stop/navigation supersedes this playback; cancellation is a successful local action.
      if (!request.signal.aborted && generation === this.generation) {
        this.stop();
        throw error;
      }
    }
  }
}
