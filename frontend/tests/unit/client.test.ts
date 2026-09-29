import { afterEach, expect, test, vi } from "vitest";
import { sendCommand, type Session } from "../../src/api/client";

afterEach(() => vi.unstubAllGlobals());

test("Pause retries a revision conflict with the same intent and ownership", async () => {
  const session = {
    id: "session",
    revision: 8,
    connection_epoch: "epoch",
    lifecycle: "in_progress",
    input: { id: "input" },
  } as Session;
  const fresh = { ...session, revision: 9 };
  const stopped = { ...fresh, revision: 10, lifecycle: "paused" };
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ code: "conflict" }), { status: 409 }),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify(fresh)))
    .mockResolvedValueOnce(new Response(JSON.stringify(stopped)));
  vi.stubGlobal("fetch", fetcher);
  expect(await sendCommand(session, "pause")).toEqual(stopped);
  const first = JSON.parse(fetcher.mock.calls[0][1].body);
  const retry = JSON.parse(fetcher.mock.calls[2][1].body);
  expect(retry).toEqual({ ...first, expected_revision: 9 });
});

test("a conflicting command cannot cross into a new connection", async () => {
  const session = {
    id: "session",
    revision: 8,
    connection_epoch: "old",
    input: null,
  } as Session;
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ code: "conflict" }), { status: 409 }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({ ...session, revision: 9, connection_epoch: "new" }),
      ),
    );
  vi.stubGlobal("fetch", fetcher);
  await expect(sendCommand(session, "pause")).rejects.toThrow(
    "stale_connection",
  );
  expect(fetcher).toHaveBeenCalledTimes(2);
});
