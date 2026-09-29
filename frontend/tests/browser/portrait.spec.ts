import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
const content = JSON.parse(
  readFileSync("../content/workplace-english.json", "utf8"),
);

test.beforeEach(async ({ page }) => {
  await page.route("**/api/guest", (route) =>
    route.fulfill({ json: { available: true } }),
  );
  await page.route("**/api/content", (route) =>
    route.fulfill({ json: content }),
  );
  await page.route("**/api/sessions", (route) => route.fulfill({ json: [] }));
});

async function fits(page: import("@playwright/test").Page) {
  expect(
    await page
      .locator(".scroll-area")
      .evaluate((e) => e.scrollHeight - e.clientHeight),
    `Content overflow at ${JSON.stringify(page.viewportSize())}: ${await page.locator("h1").textContent()}`,
  ).toBeLessThanOrEqual(2);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  const geometry = await page.locator(".portrait").boundingBox();
  expect(geometry!.width).toBeLessThanOrEqual(390);
  expect(geometry!.height).toBeLessThanOrEqual(844);
  for (const target of await page
    .locator("button:visible, summary:visible, .entry-disclosure")
    .all()) {
    const box = await target.boundingBox();
    expect(
      box!.width,
      (await target.textContent()) ?? "",
    ).toBeGreaterThanOrEqual(44);
    expect(
      box!.height,
      (await target.textContent()) ?? "",
    ).toBeGreaterThanOrEqual(44);
    await expect(target).toBeInViewport();
  }
}

test("scenario cards and the start flow fit the phone without scrolling", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () => {
      throw new Error("Browsing must not request a microphone");
    };
  });
  for (const viewport of [
    { width: 390, height: 844 },
    { width: 320, height: 640 },
    { width: 360, height: 740 },
    { width: 800, height: 800 },
    { width: 1440, height: 1000 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.locator(".scenario-card")).toHaveCount(3);
    await fits(page);
    if (viewport.width === 390)
      await page.screenshot({ path: "../.cache/evidence/phone-home-390.png" });
    if (viewport.width === 320 || viewport.width === 360)
      await page.screenshot({
        path: `../.cache/evidence/phone-home-${viewport.width}.png`,
      });
    await page
      .getByRole("button", { name: "Hosting a meeting", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Hosting a meeting" }),
    ).toBeVisible();
    await fits(page);
    if (viewport.width === 390)
      await page.screenshot({
        path: "../.cache/evidence/phone-purposes-390.png",
      });
    await page
      .getByRole("button", { name: "Welcome everyone", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Start practice" }),
    ).toBeDisabled();
    await page.getByRole("checkbox").check();
    await expect(
      page.getByRole("button", { name: "Start practice" }),
    ).toBeEnabled();
    await fits(page);
    if (viewport.width === 390)
      await page.screenshot({
        path: "../.cache/evidence/phone-expression-390.png",
      });
    if (viewport.width === 320)
      await page.screenshot({
        path: "../.cache/evidence/phone-expression-320.png",
      });
    const situation = page.locator("summary", {
      hasText: "Your practice situation",
    });
    await situation.click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(
      page
        .locator("details[open]")
        .getByText(content.purposes[0].preset_situation),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Start practice" }),
    ).toBeInViewport();
    if (viewport.width === 390)
      await page.screenshot({
        path: "../.cache/evidence/phone-situation-390.png",
      });
    await situation.click();
    await fits(page);
  }
  await page.goto("/");
  await page
    .getByRole("button", { name: "Hosting a meeting", exact: true })
    .focus();
  await page.keyboard.press("Tab");
  const second = page.getByRole("button", { name: "One-on-one", exact: true });
  await expect(second).toBeFocused();
  await expect(second).toHaveCSS("outline-style", "solid");
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Share progress", exact: true }),
  ).toBeVisible();
});

test("completed review never connects or requests a microphone", async ({
  page,
}) => {
  const session = emptySession();
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () => {
      throw new Error("Review must not request microphone");
    };
  });
  const connections: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/connect")) connections.push(request.url());
  });
  await page.route(`**/api/sessions/${session.id}`, (route) =>
    route.fulfill({ json: session }),
  );
  await page.route("**/events", (route) =>
    route.fulfill({ contentType: "text/event-stream", body: ": fixture\n\n" }),
  );
  await page.goto(`/?session=${session.id}`);
  await expect(
    page.getByRole("heading", { name: "Take it into your day." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Resume practice" }),
  ).toHaveCount(0);
  await page.reload();
  await expect(page.getByText("A phrase to take with you")).toBeVisible();
  expect(connections).toHaveLength(0);
  await page.screenshot({ path: "test-results/review-empty-390.png" });
});

test("all nine purposes and inline examples need no microphone", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () => {
      throw new Error("Browsing needs no mic");
    };
  });
  await page.goto("/");
  for (const viewport of [
    { width: 390, height: 844 },
    { width: 320, height: 640 },
  ]) {
    await page.setViewportSize(viewport);
    for (const [index, title] of [
      "Hosting a meeting",
      "One-on-one",
      "Casual talk",
    ].entries()) {
      await page.getByRole("button", { name: title, exact: true }).click();
      for (const purpose of content.purposes.slice(index * 3, index * 3 + 3)) {
        await page
          .getByRole("button", { name: purpose.title, exact: true })
          .click();
        await expect(
          page.getByRole("heading", { name: purpose.title, exact: true }),
        ).toBeVisible();
        await expect(
          page.getByText(purpose.expression, { exact: true }),
        ).toBeVisible();
        await fits(page);
        await page.locator("summary", { hasText: "More examples" }).click();
        await expect(
          page.getByText(purpose.alternative, { exact: true }),
        ).toBeVisible();
        await expect(
          page.getByText(purpose.example, { exact: true }),
        ).toBeVisible();
        await expect(
          page.getByRole("button", { name: "Start practice" }),
        ).toBeInViewport();
        const situation = page.locator("summary", {
          hasText: "Your practice situation",
        });
        await situation.click();
        await expect(page.getByRole("dialog")).toHaveCount(0);
        await expect(page.locator("details[open]")).toHaveCount(1);
        await expect(
          page.getByText(purpose.alternative, { exact: true }),
        ).toBeHidden();
        await expect(
          page.getByText(purpose.preset_situation, { exact: true }),
        ).toBeVisible();
        await situation.click();
        await expect(situation).toBeFocused();
        await fits(page);
        await page
          .getByRole("button", { name: "Back to purposes", exact: true })
          .click();
      }
      await page
        .getByRole("button", { name: "Back to conversations", exact: true })
        .click();
    }
  }
  await page
    .getByRole("button", { name: "Recent sessions", exact: true })
    .click();
  await expect(
    page.getByText(
      "No sessions yet. Start a conversation to save your practice here.",
    ),
  ).toBeVisible();
});

function emptySession() {
  return {
    schema_version: 1,
    id: "a".repeat(32),
    guest_id: "b".repeat(32),
    purpose_id: "welcome-everyone",
    content_version: "test",
    conversation_model: "test",
    prompt_version: "test",
    revision: 3,
    sequence: 3,
    lifecycle: "completed",
    phase: "coaching",
    substate: "ready",
    created_at: 1,
    last_practice_at: 1,
    expires_at: 9999999999,
    completed_at: 2,
    connection_epoch: null,
    room: null,
    participant: null,
    generation_id: "c".repeat(32),
    situation: "A weekly meeting",
    setup: null,
    question_id: null,
    answers: [],
    messages: [],
    input: null,
    pending_command: null,
    receipts: {},
    assessment: { status: "none", result: null },
    notice: null,
    retries: [],
    coaching_turns: [],
    helper: null,
    capture_muted: false,
  };
}

test("saved feedback uses sheets and leaves primary actions inside the phone", async ({
  page,
}) => {
  const session = {
    ...emptySession(),
    answers: [
      {
        id: "answer",
        question_id: "opening",
        transcript: { text: "Let's agree on the next steps." },
      },
    ],
    messages: [
      {
        id: "opening",
        text: "How would you open our meeting?",
        delivery: "completed",
      },
    ],
    assessment: {
      status: "ready",
      result: {
        dimensions: {
          naturalness: {
            status: "scored",
            score: 4,
            explanation: "The phrasing is clear and natural.",
            evidence: [
              {
                quote: "agree on the next steps",
                observation: "This makes the intended outcome clear.",
              },
            ],
          },
          workplace_tone: {
            status: "scored",
            score: 4,
            explanation: "The invitation sounds collaborative.",
            evidence: [],
          },
        },
        retry_priority: {
          suggestion: "Name the outcome so everyone knows what to aim for.",
        },
        modeled_example:
          "Let's agree on our next steps before we finish today.",
        spoken_summary:
          "You opened with a clear purpose. Keep that collaborative tone.",
        strengths: [],
        issues: [],
        takeaway:
          "A clear outcome helps everyone move the conversation forward.",
      },
    },
  };
  await page.route(`**/api/sessions/${session.id}`, (route) =>
    route.fulfill({ json: session }),
  );
  await page.route("**/events", (route) =>
    route.fulfill({ contentType: "text/event-stream", body: ": fixture\n\n" }),
  );
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () => {
      throw new Error("Review needs no microphone");
    };
  });
  await page.goto(`/?session=${session.id}`);
  await expect(
    page.getByRole("button", { name: "Listen to your takeaway" }),
  ).toBeVisible();
  await fits(page);
  await page.screenshot({ path: "../.cache/evidence/phone-takeaway-390.png" });
  await page.getByRole("button", { name: "Feedback & scores" }).click();
  await expect(
    page.getByText("Based on your words", { exact: true }),
  ).toBeVisible();
  await fits(page);
  await page.screenshot({ path: "../.cache/evidence/phone-feedback-390.png" });
  await page.getByRole("button", { name: /Naturalness/ }).click();
  await expect(
    page.getByRole("dialog").getByText("The phrasing is clear and natural."),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /Coaching notes/ }).click();
  await expect(
    page
      .getByRole("dialog")
      .getByText(session.assessment.result.modeled_example, { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close details" }).click();
  await page.getByRole("button", { name: "Show words" }).click();
  await expect(
    page.getByRole("dialog").getByText(session.answers[0].transcript.text),
  ).toBeVisible();
  await page.screenshot({
    path: "../.cache/evidence/phone-transcript-390.png",
  });
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Practice again", exact: true }),
  ).toBeInViewport();
});

test("starting from a purpose preserves selection and requires disclosure", async ({
  page,
}) => {
  let selectedPurpose: string | undefined;
  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() === "POST") {
      selectedPurpose = route.request().postDataJSON().purpose_id;
      await route.fulfill({ status: 503, json: { code: "voice_busy" } });
    } else await route.fulfill({ json: [] });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "One-on-one", exact: true }).click();
  await page
    .getByRole("button", { name: "Ask for feedback", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Start practice" }),
  ).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Start practice" }).click();
  await expect.poll(() => selectedPurpose).toBe("ask-for-feedback");
  await expect(page.getByRole("alert")).toBeVisible();
});
