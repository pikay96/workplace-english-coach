import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";

test("Recent sessions shows only this browser's real API records", async ({
  page,
  browser,
  baseURL,
}) => {
  test.skip(
    !process.env.TEST_APP_URL,
    "Requires the running application and Redis.",
  );
  const headers = { origin: new URL(baseURL!).origin };
  await page.goto("/");
  await expect(page.locator(".scenario-card")).toHaveCount(3);
  const recent = page.getByRole("button", {
    name: "Recent sessions",
    exact: true,
  });
  await recent.click();
  await expect(page.locator(".recent-row")).toHaveCount(0);

  // This browser context owns its own guest cookie. No user history is touched.
  const created = await page.request.post("/api/sessions", {
    headers,
    data: {
      purpose_id: "ask-for-feedback",
      command_id: randomUUID().replaceAll("-", ""),
    },
  });
  expect(created.ok()).toBe(true);
  const session = await created.json();
  try {
    await page.reload();
    await page
      .getByRole("button", { name: "Recent sessions", exact: true })
      .click();
    await expect(page.locator(".recent-row")).toHaveCount(1);
    await expect(
      page
        .locator(".recent-row")
        .getByRole("button", { name: /^Ask for feedback Resume/ }),
    ).toBeVisible();
    await expect(page.locator(".recent-row time")).toHaveAttribute(
      "datetime",
      new Date(session.last_practice_at * 1000).toISOString(),
    );

    const otherGuest = await browser.newContext({ baseURL });
    try {
      const stranger = await otherGuest.newPage();
      await stranger.goto("/");
      await expect(stranger.locator(".scenario-card")).toHaveCount(3);
      await stranger
        .getByRole("button", { name: "Recent sessions", exact: true })
        .click();
      await expect(stranger.locator(".recent-row")).toHaveCount(0);
    } finally {
      await otherGuest.close();
    }

    await page.getByRole("button", { name: "Delete session" }).click();
    await expect(page.locator(".recent-row")).toHaveCount(0);
    const remaining = await page.request.get("/api/sessions");
    expect(await remaining.json()).toEqual([]);
  } finally {
    await page.request.delete(`/api/sessions/${session.id}`, { headers });
  }
});
