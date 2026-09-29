import { expect, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";
import type { Session } from "../../src/api/client";

test.skip(
  process.env.LIVE_VOICE_TEST !== "1",
  "Explicit opt-in: billable LiveKit calls.",
);
test.setTimeout(240_000);
test.use({ actionTimeout: 10_000 });

let fixtures: Record<string, string>;
test.beforeAll(() => {
  const python =
    process.env.TEST_PYTHON ??
    path.resolve("../backend/.venv/Scripts/python.exe");
  const local = process.platform === "win32";
  fixtures = JSON.parse(
    execFileSync(
      local ? "powershell.exe" : python,
      local
        ? ["-NoProfile", "-File", "tests/live/audio_fixtures.ps1"]
        : ["tests/live/audio_fixtures.py"],
      {
        cwd: path.resolve("../backend"),
        encoding: "utf8",
        timeout: 150_000,
        env: { ...process.env, PYTHONPATH: "." },
        maxBuffer: 32 * 1024 * 1024,
      },
    ),
  );
});

async function installAudio(page: Page) {
  await page.addInitScript(() => {
    let context: AudioContext;
    let destination: MediaStreamAudioDestinationNode;
    let micRequests = 0;
    let audibleSamples = 0;
    let firstAudioAt = 0;
    let lastAudioAt = 0;
    let maxAudioGapMs = 0;
    let source: AudioBufferSourceNode | undefined;
    const analyzers: AnalyserNode[] = [];
    const connect = AudioNode.prototype.connect;
    AudioNode.prototype.connect = function (
      destination: AudioNode,
      ...args: any[]
    ) {
      if (destination instanceof AudioDestinationNode) {
        const analyzer = this.context.createAnalyser();
        connect.call(this, analyzer);
        analyzers.push(analyzer);
      }
      return (connect as any).call(this, destination, ...args);
    } as typeof connect;
    const observed = new WeakSet<HTMLMediaElement>();
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () {
      if (this.srcObject instanceof MediaStream && !observed.has(this)) {
        observed.add(this);
        const monitor = new AudioContext();
        const analyzer = monitor.createAnalyser();
        monitor.createMediaStreamSource(this.srcObject).connect(analyzer);
        analyzers.push(analyzer);
        void monitor.resume();
      }
      return play.call(this);
    };
    setInterval(() => {
      for (const analyzer of analyzers) {
        const samples = new Float32Array(analyzer.fftSize);
        analyzer.getFloatTimeDomainData(samples);
        if (samples.some((v) => Math.abs(v) > 0.002)) {
          audibleSamples++;
          if (lastAudioAt)
            maxAudioGapMs = Math.max(maxAudioGapMs, Date.now() - lastAudioAt);
          firstAudioAt ||= Date.now();
          lastAudioAt = Date.now();
        }
      }
    }, 20);
    navigator.mediaDevices.getUserMedia = async () => {
      micRequests++;
      context = new AudioContext({ sampleRate: 24000 });
      destination = context.createMediaStreamDestination();
      await context.resume();
      return destination.stream;
    };
    Object.assign(window, {
      fixtureAudio: {
        stats: () => ({
          micRequests,
          audibleSamples,
          firstAudioAt,
          lastAudioAt,
          maxAudioGapMs,
          micEnabled:
            destination?.stream.getAudioTracks()[0]?.readyState === "live" &&
            destination.stream.getAudioTracks()[0].enabled,
          micState: destination?.stream.getAudioTracks()[0]?.readyState,
        }),
        stop: () => source?.stop(),
        send: async (encoded: string, loop = false) => {
          const bytes = Uint8Array.from(atob(encoded), (v) => v.charCodeAt(0));
          const view = new DataView(bytes.buffer);
          const buffer = context.createBuffer(1, bytes.length / 2, 24000);
          const channel = buffer.getChannelData(0);
          for (let i = 0; i < channel.length; i++)
            channel[i] = view.getInt16(i * 2, true) / 32768;
          source = context.createBufferSource();
          source.buffer = buffer;
          source.loop = loop;
          if (loop) {
            let first = 0,
              last = channel.length - 1;
            while (first < last && Math.abs(channel[first]) < 0.005) first++;
            while (last > first && Math.abs(channel[last]) < 0.005) last--;
            source.loopStart = Math.max(0, first / 24000 - 0.02);
            source.loopEnd = Math.min(buffer.duration, last / 24000 + 0.02);
          }
          source.connect(destination);
          if (loop) {
            source.start();
            return;
          }
          await new Promise<void>((resolve) => {
            source.onended = () => resolve();
            source.start();
          });
        },
      },
    });
  });
}

async function snapshot(page: Page): Promise<Session> {
  return page.evaluate(async () => {
    const id = new URL(location.href).searchParams.get("session");
    const response = await fetch(`/api/sessions/${id}`);
    if (!response.ok) throw new Error(`snapshot:${response.status}`);
    return response.json();
  });
}

async function waitFor(
  page: Page,
  condition: (s: Session) => boolean,
  timeout = 75_000,
) {
  await expect
    .poll(
      async () => {
        const s = await snapshot(page);
        if (
          s.substate === "unavailable" ||
          s.assessment.status === "unavailable"
        ) {
          throw new Error(
            JSON.stringify({
              substate: s.substate,
              lifecycle: s.lifecycle,
              notice: s.notice,
            }),
          );
        }
        return s.lifecycle === "in_progress" && condition(s);
      },
      { timeout, intervals: [500] },
    )
    .toBe(true);
}

async function speak(page: Page, name: string) {
  await expect(
    page.getByRole("button", { name: "I’m done", exact: true }),
  ).toBeEnabled();
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).fixtureAudio.stats().micEnabled),
    )
    .toBe(true);
  await page.evaluate(
    (pcm) => (window as any).fixtureAudio.send(pcm),
    fixtures[name],
  );
}

test("real browser WebRTC: generated opening, two spoken answers, coaching, Finish and Review", async ({
  page,
}) => {
  test.setTimeout(360_000);
  await installAudio(page);
  const started = Date.now();
  await page.goto("/");
  await page
    .getByRole("button", { name: "Hosting a meeting", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Welcome everyone", exact: true })
    .click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Start practice" }).click();
  await expect(page).toHaveURL(/session=/);
  await waitFor(page, (s) => s.messages[0]?.delivery === "completed");
  const openingMs = Date.now() - started;
  const firstAudioMs =
    (await page.evaluate(
      () => (window as any).fixtureAudio.stats().firstAudioAt,
    )) - started;
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).fixtureAudio.stats().audibleSamples),
    )
    .toBeGreaterThan(5);
  await speak(page, "welcome");
  await waitFor(
    page,
    (s) =>
      s.answers.length === 1 && s.messages.at(-1)?.delivery === "completed",
  );
  await speak(page, "goal");
  await waitFor(
    page,
    (s) =>
      s.assessment.status === "ready" &&
      s.messages.at(-1)?.kind === "coaching" &&
      s.messages.at(-1)?.delivery === "completed",
    // This waits for both bridge and coaching speech, plus the assessment.
    // Each playback has its own 90-second application bound; this is a
    // correctness check, not a passed latency target.
    220_000,
  );
  const saved = await snapshot(page);
  expect(saved.answers).toHaveLength(2);
  expect(saved.messages.map((m) => m.kind)).toEqual([
    "opening",
    "follow_up",
    "bridge",
    "coaching",
  ]);
  const result = saved.assessment.result!;
  for (const dimension of Object.values(result.dimensions)) {
    expect(dimension.status).toBe("scored");
    expect(dimension.score).toBeGreaterThanOrEqual(1);
    for (const evidence of dimension.evidence) {
      const answer = saved.answers.find((a) => a.id === evidence.turn_id)!;
      expect(evidence.answer_revision).toBe(answer.revision);
      if (evidence.quote !== null)
        expect(answer.transcript.text).toContain(evidence.quote);
    }
  }
  for (const m of saved.messages) expect(m.played_text).toBe(m.text);
  await page
    .getByRole("button", { name: "Finish practice", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Take it into your day." }),
  ).toBeVisible();
  const finished = await snapshot(page);
  expect(finished.lifecycle).toBe("completed");
  await page.reload();
  await page.getByRole("button", { name: "Feedback & scores" }).click();
  await expect(
    page.getByText("Based on your words", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().micRequests),
  ).toBe(0);
  expect((await snapshot(page)).assessment.result).toEqual(result);
  const reviewConnections: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/connect"))
      reviewConnections.push(request.url());
  });
  await page.getByRole("button", { name: "Takeaway", exact: true }).click();
  await page.getByRole("button", { name: "Listen to your takeaway" }).click();
  await expect
    .poll(
      () =>
        page.evaluate(
          () => (window as any).fixtureAudio.stats().audibleSamples,
        ),
      { timeout: 40_000 },
    )
    .toBeGreaterThan(3);
  await page.getByRole("button", { name: "Stop audio", exact: true }).click();
  await page.waitForTimeout(500);
  const reviewStoppedAt = await page.evaluate(
    () => (window as any).fixtureAudio.stats().lastAudioAt,
  );
  await page.waitForTimeout(1000);
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().lastAudioAt),
  ).toBe(reviewStoppedAt);
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().micRequests),
  ).toBe(0);
  expect(reviewConnections).toHaveLength(0);
  await page.locator(".scroll-area").evaluate((element) => {
    element.scrollTop = 0;
  });
  await page.screenshot({
    path: path.resolve("../.cache/evidence/live-review-390.png"),
    fullPage: true,
  });
  console.log(
    JSON.stringify({
      opening_completed_ms: openingMs,
      opening_first_audio_ms: firstAudioMs,
      journey_ms: Date.now() - started,
      accepted_answers: 2,
      actual_inference: true,
      browser_webrtc: true,
    }),
  );
});

async function startPractice(page: Page) {
  await installAudio(page);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Hosting a meeting", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Welcome everyone", exact: true })
    .click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Start practice" }).click();
  await expect(page).toHaveURL(/session=/);
}

test("Alex asks first with audible playback before opening the microphone", async ({
  page,
}) => {
  await startPractice(page);
  let id: string | undefined;
  try {
    const beginning = await snapshot(page);
    id = beginning.id;
    expect(beginning.answers).toHaveLength(0);
    expect(beginning.input).toBeNull();
    expect(
      await page.evaluate(
        () => (window as any).fixtureAudio.stats().micEnabled,
      ),
    ).toBe(false);
    await waitFor(page, (s) => s.messages[0]?.delivery === "completed");
    const saved = await snapshot(page);
    expect(saved.messages[0].text).toMatch(/\?$/);
    expect(saved.messages[0].text.match(/\?/g)).toHaveLength(1);
    expect(saved.messages[0].played_text).toBe(saved.messages[0].text);
    expect(saved.answers).toHaveLength(0);
    expect(saved.substate).toBe("listening");
    await expect
      .poll(() =>
        page.evaluate(() => (window as any).fixtureAudio.stats().micEnabled),
      )
      .toBe(true);
    const stats = await page.evaluate(() =>
      (window as any).fixtureAudio.stats(),
    );
    console.log(
      JSON.stringify({
        opening: saved.messages[0].text,
        ...stats,
        actual_webrtc: true,
      }),
    );
    expect(stats.audibleSamples).toBeGreaterThan(20);
    // Quiet amplitude windows include the voice's intentional sentence pauses.
    // Keep them as observations, not a continuity verdict. Delayed-chunk tests
    // and check_speech_continuity.py verify that delivery cannot starve playout.
  } finally {
    if (id)
      await page.request.delete(`/api/sessions/${id}`, {
        headers: {
          Origin: "http://localhost:8080",
          "X-Requested-With": "workplace-english",
        },
      });
  }
});

test("speech during Alex playback is ignored; Pause stops output; Resume and manual done work", async ({
  page,
}) => {
  test.setTimeout(360_000);
  await startPractice(page);
  await expect
    .poll(
      () =>
        page.evaluate(
          () => (window as any).fixtureAudio.stats().audibleSamples,
        ),
      { timeout: 60_000 },
    )
    .toBeGreaterThan(5);
  const before = await snapshot(page);
  expect(before.input).toBeNull();
  expect(before.messages[0].delivery).toBe("playing");
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().micEnabled),
  ).toBe(false);
  await expect(
    page.getByRole("button", { name: "I’m done", exact: true }),
  ).toBeDisabled();
  const overlap = page.evaluate(
    (pcm) => (window as any).fixtureAudio.send(pcm),
    fixtures.welcome,
  );
  await page.waitForTimeout(750);
  await page.evaluate(() => (window as any).fixtureAudio.stop());
  await overlap;
  const during = await snapshot(page);
  expect(during.input).toBeNull();
  expect(during.answers).toHaveLength(0);
  expect(during.messages[0].delivery).toBe("playing");
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  const paused = await snapshot(page);
  expect(paused.lifecycle).toBe("paused");
  expect(paused.input).toBeNull();
  expect(paused.answers).toHaveLength(0);
  expect(paused.messages[0].played_text).toBeNull();
  await page.waitForTimeout(1000);
  const lastAudioAt = await page.evaluate(
    () => (window as any).fixtureAudio.stats().lastAudioAt,
  );
  await page.waitForTimeout(2000);
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().lastAudioAt),
  ).toBe(lastAudioAt);
  await page.getByRole("button", { name: "Resume practice" }).click();
  await waitFor(page, (s) => s.messages[0]?.delivery === "completed");
  expect((await snapshot(page)).input?.first_speech_at).toBeNull();
  expect((await snapshot(page)).answers).toHaveLength(0);
  // Once Alex has finished, actual learner speech starts an answer. Pause discards it.
  const answer = speak(page, "welcome");
  await waitFor(page, (s) => s.input?.first_speech_at != null, 15_000);
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await answer;
  expect((await snapshot(page)).answers).toHaveLength(0);
  expect((await snapshot(page)).input).toBeNull();
  await page.getByRole("button", { name: "Resume practice" }).click();
  await waitFor(page, (s) => s.input?.status === "open");
  await speak(page, "welcome");
  await page.getByRole("button", { name: "I’m done", exact: true }).click();
  await waitFor(
    page,
    (s) =>
      s.answers.length === 1 && s.messages.at(-1)?.delivery === "completed",
  );
  expect((await snapshot(page)).messages).toHaveLength(2);
  await page.getByRole("button", { name: "Finish practice" }).click();
});

test("three spoken answers close the roleplay and never open a fourth input", async ({
  page,
}) => {
  await startPractice(page);
  await waitFor(page, (s) => s.messages[0]?.delivery === "completed");
  for (let count = 1; count <= 2; count++) {
    await speak(page, count === 1 ? "brief" : "agenda");
    await waitFor(
      page,
      (s) =>
        s.answers.length === count &&
        s.messages.at(-1)?.delivery === "completed",
    );
    expect((await snapshot(page)).phase).toBe("roleplay");
  }
  await speak(page, "welcome");
  await waitFor(page, (s) => s.answers.length === 3 && s.phase === "coaching");
  const saved = await snapshot(page);
  expect(saved.input).toBeNull();
  expect(saved.messages.filter((m) => m.kind === "follow_up")).toHaveLength(2);
  expect(saved.messages.at(-1)?.kind).toBe("bridge");
  await page.getByRole("button", { name: "Finish practice" }).click();
});

test("real 60-second cue and 120-second cap require explicit discard or submit", async ({
  page,
}) => {
  test.setTimeout(420_000);
  await startPractice(page);
  await waitFor(page, (s) => s.messages[0]?.delivery === "completed");
  const first = await snapshot(page);
  for (const choice of ["Try again", "Use this answer"]) {
    const before = await snapshot(page);
    await page.evaluate(
      (pcm) => (window as any).fixtureAudio.send(pcm, true),
      fixtures.long_answer,
    );
    await waitFor(page, (s) => s.input?.cue_shown === true, 70_000);
    await expect(
      page.getByText("Wrap up your answer when you’re ready."),
    ).toBeVisible();
    await waitFor(
      page,
      (s) => s.input?.status === "awaiting_limit_confirmation",
      75_000,
    );
    await page.evaluate(() => (window as any).fixtureAudio.stop());
    const capped = await snapshot(page);
    expect(capped.answers).toHaveLength(0);
    expect(capped.input?.id).toBe(before.input?.id);
    expect(capped.input?.capture_seconds).toBe(120);
    expect(capped.question_id).toBe(first.question_id);
    await page.getByRole("button", { name: choice, exact: true }).click();
    if (choice === "Try again") {
      await waitFor(
        page,
        (s) => s.input?.status === "open" && s.input.id !== capped.input?.id,
      );
      expect((await snapshot(page)).answers).toHaveLength(0);
    } else {
      await waitFor(page, (s) => s.answers.length === 1);
      const accepted = (await snapshot(page)).answers[0];
      expect(accepted.input_id).toBe(capped.input?.id);
      expect(accepted.capture_limited).toBe(true);
    }
  }
  await page.getByRole("button", { name: "Finish practice" }).click();
});

test("coaching question and focused retry keep original scores, then Practice again varies opening", async ({
  page,
}) => {
  test.setTimeout(900_000);
  await startPractice(page);
  await waitFor(page, (s) => s.substate === "listening", 110_000);
  await speak(page, "welcome");
  await waitFor(
    page,
    (s) => s.answers.length === 1 && s.substate === "listening",
    110_000,
  );
  await speak(page, "goal");
  await waitFor(
    page,
    (s) =>
      s.phase === "coaching" &&
      s.substate === "listening" &&
      s.assessment.status === "ready",
    240_000,
  );
  const original = await snapshot(page);
  await speak(page, "coaching_question");
  await waitFor(
    page,
    (s) => s.coaching_turns.length === 1 && s.substate === "listening",
    110_000,
  );
  expect((await snapshot(page)).assessment).toEqual(original.assessment);
  expect((await snapshot(page)).answers).toEqual(original.answers);
  await page.getByRole("button", { name: "Try this suggestion" }).click();
  await waitFor(
    page,
    (s) => s.phase === "retry" && s.substate === "listening",
    110_000,
  );
  await speak(page, "goal");
  await waitFor(
    page,
    (s) =>
      s.retries[0].answers.length === 1 &&
      (s.substate === "listening" ||
        s.retries[0].assessment.status === "ready"),
    220_000,
  );
  let retry = (await snapshot(page)).retries[0];
  if (retry.assessment.status === "none") {
    await speak(page, "welcome");
  }
  await waitFor(
    page,
    (s) =>
      s.phase === "coaching" &&
      s.substate === "listening" &&
      s.retries[0].assessment.status === "ready",
    220_000,
  );
  const after = await snapshot(page);
  expect(after.assessment).toEqual(original.assessment);
  expect(after.answers).toEqual(original.answers);
  expect(after.retries[0].answers.length).toBeLessThanOrEqual(2);
  for (const evidence of after.retries[0].assessment.result!.evidence)
    expect(
      after.retries[0].answers.some((a) => a.id === evidence.turn_id),
    ).toBe(true);
  await page
    .getByRole("button", { name: "Finish practice", exact: true })
    .click();
  await page.reload();
  await expect(
    page.getByText("Focused retry 1 · Based on your words"),
  ).toBeVisible();
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().micRequests),
  ).toBe(0);
  await page
    .getByRole("button", { name: "Practice again", exact: true })
    .click();
  await waitFor(page, (s) => s.substate === "listening", 110_000);
  const fresh = await snapshot(page);
  expect(fresh.id).not.toBe(original.id);
  expect(fresh.source_session_id).toBe(original.id);
  expect(fresh.answers).toHaveLength(0);
  expect(fresh.messages[0].text.trim().toLowerCase()).not.toBe(
    original.messages[0].text.trim().toLowerCase(),
  );
  await page
    .getByRole("button", { name: "Finish practice", exact: true })
    .click();
});

test("Hint, replay, mute, continuation, and competing tab preserve alternating turns", async ({
  page,
  context,
}) => {
  test.setTimeout(720_000);
  await startPractice(page);
  await waitFor(page, (s) => s.substate === "listening", 110_000);
  await speak(page, "welcome");
  await waitFor(
    page,
    (s) => s.answers.length === 1 && s.substate === "listening",
    110_000,
  );
  const before = await snapshot(page);
  await page
    .getByRole("button", { name: "I wasn’t finished", exact: true })
    .click();
  await speak(page, "goal");
  await waitFor(
    page,
    (s) => s.answers[0].revision === 2 && s.substate === "listening",
    110_000,
  );
  const continued = await snapshot(page);
  expect(continued.answers).toHaveLength(1);
  expect(continued.answers[0].id).toBe(before.answers[0].id);
  expect(continued.answers[0].capture_seconds).toBeGreaterThan(
    before.answers[0].capture_seconds,
  );
  await page.getByRole("button", { name: "Mute", exact: true }).click();
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).fixtureAudio.stats().micEnabled),
    )
    .toBe(false);
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().micState),
  ).toBe("ended");
  expect((await snapshot(page)).input).toBeNull();
  const messageCount = continued.messages.length;
  const previousPlayback = continued.messages.at(-1)?.playback_id;
  await page.getByRole("button", { name: "Hear Alex", exact: true }).click();
  await waitFor(
    page,
    (s) =>
      s.substate === "ready" &&
      s.messages.at(-1)?.delivery === "completed" &&
      s.messages.at(-1)?.playback_id !== previousPlayback,
    110_000,
  );
  expect((await snapshot(page)).messages).toHaveLength(messageCount);
  expect((await snapshot(page)).input).toBeNull();
  await page.getByRole("button", { name: "Unmute", exact: true }).click();
  await waitFor(page, (s) => s.substate === "listening");
  await page.getByRole("button", { name: "Hint", exact: true }).click();
  await expect
    .poll(async () => (await snapshot(page)).helper?.status, { timeout: 20000 })
    .toBe("ready");
  const hinted = await snapshot(page);
  expect(hinted.lifecycle).toBe("paused");
  expect(hinted.input).toBeNull();
  expect(hinted.answers).toEqual(continued.answers);
  await page.getByRole("button", { name: "Stop audio", exact: true }).click();
  await page
    .getByRole("button", { name: "Resume practice", exact: true })
    .click();
  await waitFor(page, (s) => s.substate === "listening", 110_000);
  const oldEpoch = (await snapshot(page)).connection_epoch;
  const second = await context.newPage();
  await installAudio(second);
  await second.goto(page.url());
  await second
    .getByRole("button", { name: "Resume practice", exact: true })
    .click();
  await waitFor(second, (s) => s.substate === "listening", 110_000);
  expect((await snapshot(second)).connection_epoch).not.toBe(oldEpoch);
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).fixtureAudio.stats().micEnabled),
    )
    .toBe(false);
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().micState),
  ).toBe("ended");
  expect((await snapshot(second)).answers).toEqual(continued.answers);
  await second
    .getByRole("button", { name: "Finish practice", exact: true })
    .click();
  await second.close();
});

test("real framed HTTP expression playback is audible, cancellable and needs no microphone", async ({
  page,
}) => {
  test.setTimeout(90000);
  await installAudio(page);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Hosting a meeting", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Welcome everyone", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Listen to the phrase", exact: true })
    .click();
  await expect
    .poll(
      () =>
        page.evaluate(
          () => (window as any).fixtureAudio.stats().audibleSamples,
        ),
      { timeout: 30000 },
    )
    .toBeGreaterThan(3);
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().micRequests),
  ).toBe(0);
  await page.getByRole("button", { name: "Stop audio", exact: true }).click();
  await page.waitForTimeout(500);
  const stopped = await page.evaluate(
    () => (window as any).fixtureAudio.stats().lastAudioAt,
  );
  await page.waitForTimeout(1500);
  expect(
    await page.evaluate(() => (window as any).fixtureAudio.stats().lastAudioAt),
  ).toBe(stopped);
});
