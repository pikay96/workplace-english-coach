/** Incremental wire decoder; chunk boundaries may split a header or a PCM frame. */
export class PcmFrames {
  private pending = new Uint8Array(0);
  completed = false;

  push(chunk: Uint8Array): Uint8Array[] {
    if (this.completed && chunk.length)
      throw new Error("audio_after_completion");
    const joined = new Uint8Array(this.pending.length + chunk.length);
    joined.set(this.pending);
    joined.set(chunk, this.pending.length);
    const frames: Uint8Array[] = [];
    let offset = 0;
    while (joined.length - offset >= 4) {
      const length = new DataView(joined.buffer).getUint32(offset, false);
      if (length === 0xffffffff) throw new Error("playback_unavailable");
      if (length === 0) {
        this.completed = true;
        offset += 4;
        if (offset !== joined.length) throw new Error("audio_after_completion");
        break;
      }
      if (length > 192000 || length % 2) throw new Error("invalid_audio_frame");
      if (joined.length - offset - 4 < length) break;
      frames.push(joined.slice(offset + 4, offset + 4 + length));
      offset += 4 + length;
    }
    this.pending = joined.slice(offset);
    return frames;
  }

  finish() {
    if (!this.completed || this.pending.length)
      throw new Error("audio_incomplete");
  }
}
