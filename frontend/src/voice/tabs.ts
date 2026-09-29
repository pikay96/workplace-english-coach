/** Cooperating tabs stop locally; the server's epoch remains the final authority. */
export class TabOwnership {
  private channel?: BroadcastChannel;
  private releaseLock?: () => void;
  private waiting?: AbortController;
  private generation = 0;

  constructor(private onTaken: () => void) {}

  async acquire() {
    this.release();
    const generation = this.generation;
    if (typeof window === "undefined") return;
    if (typeof BroadcastChannel !== "undefined") {
      this.channel = new BroadcastChannel("good-company-audio");
      this.channel.onmessage = (event) => {
        if (event.data === "claim") this.onTaken();
      };
      this.channel.postMessage("claim");
    }
    if (!navigator.locks) return;
    const waiting = new AbortController();
    this.waiting = waiting;
    await new Promise<void>((resolve, reject) => {
      void navigator.locks
        .request("good-company-audio", { signal: waiting.signal }, async () => {
          if (generation !== this.generation) return resolve();
          await new Promise<void>((release) => {
            this.releaseLock = release;
            resolve();
          });
        })
        .catch((error) => (waiting.signal.aborted ? resolve() : reject(error)));
    });
  }

  release() {
    this.generation++;
    this.waiting?.abort();
    this.waiting = undefined;
    this.releaseLock?.();
    this.releaseLock = undefined;
    this.channel?.close();
    this.channel = undefined;
  }
}
