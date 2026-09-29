import type { components } from "./schema";

export type Session = components["schemas"]["Session"];
export type Content = components["schemas"]["Content"];
export type Command = components["schemas"]["Command-Input"];
export type Connection = components["schemas"]["ConnectResult"];
export type Dimension = components["schemas"]["Dimension"];

export const id = () => crypto.randomUUID().replaceAll("-", "");

export class ApiError extends Error {
  constructor(
    public code: string,
    public status: number,
  ) {
    super(code);
  }
}

export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new ApiError(
      result.code ?? result.detail ?? "service_unavailable",
      response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

/** Reconcile a revision race without changing the original input or ownership intent. */
export async function sendCommand(
  session: Session,
  type: Command["type"],
  options: Pick<Command, "expression_id" | "target_note_id"> = {},
): Promise<Session> {
  const command: Command = {
    command_id: id(),
    expected_revision: session.revision,
    connection_epoch: session.connection_epoch,
    input_id: session.input?.id,
    type,
    ...options,
  };
  for (let attempt = 0; ; attempt++) {
    try {
      return await api<Session>(`/sessions/${session.id}/commands`, command);
    } catch (error) {
      if (
        !(error instanceof ApiError) ||
        error.code !== "conflict" ||
        attempt >= 3
      )
        throw error;
      const fresh = await api<Session>(`/sessions/${session.id}`);
      if (fresh.connection_epoch !== command.connection_epoch)
        throw new ApiError("stale_connection", 409);
      if (
        fresh.lifecycle === "completed" ||
        (type === "pause" && fresh.lifecycle === "paused")
      )
        return fresh;
      command.expected_revision = fresh.revision;
    }
  }
}

export function message(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "session_unavailable")
      return "This temporary session is no longer available. Start a new practice when you’re ready.";
    if (error.code === "agent_unavailable")
      return "Alex is unavailable right now. Your session is saved. Please try again shortly.";
    if (error.code === "capacity_full")
      return "All four practice spaces are in use. Your session is saved; try again shortly.";
    if (["session_limit", "retry_limit", "coaching_limit"].includes(error.code))
      return "This practice has reached its limit. Finish to keep your results, then start a new practice.";
    if (error.code === "stale_connection")
      return "This voice connection has ended. Resume to reconnect.";
    if (error.status === 409)
      return "The session changed. Your saved progress has been refreshed; try the control again.";
  }
  return "We couldn’t connect just now. Your accepted answers are saved. Please try again.";
}
