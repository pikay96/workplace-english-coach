import { useCallback, useEffect, useRef, useState } from "react";
import { api, id, message, sendCommand } from "../api/client";
import type { Command, Connection, Content, Session } from "../api/client";
import { Feedback } from "../features/review/Feedback";
import {
  ExpressionPreview,
  PurposePicker,
  ScenarioCards,
  scenarios,
} from "../features/Conversations";
import { Sheet } from "../features/Sheet";
import { MediaController } from "../voice/controller";

function Icon({ name }: { name: string }) {
  return <img className="icon" alt="" src={`/assets/icons/${name}.svg`} />;
}

const statuses: Record<string, string> = {
  connecting: "Connecting with Alex",
  opening: "Alex is setting the scene",
  listening: "Your turn",
  thinking: "Alex is getting ready",
  speaking: "Alex is speaking",
  capped: "Keep this answer?",
  assessment_pending: "Preparing your coaching",
  ready: "Your coaching",
  unavailable: "Voice unavailable",
};

type View =
  | "home"
  | "purposes"
  | "expression"
  | "recent"
  | "practice"
  | "privacy";

export function App() {
  const [content, setContent] = useState<Content>();
  const [saved, setSaved] = useState<Session>();
  const [recent, setRecent] = useState<Session[]>([]);
  const [view, setView] = useState<View>("home");
  const [privacyReturn, setPrivacyReturn] = useState<View>("home");
  const [reviewTab, setReviewTab] = useState<"takeaway" | "feedback">(
    "takeaway",
  );
  const [practiceExpression, setPracticeExpression] = useState(false);
  const [retryDetails, setRetryDetails] = useState<string>();
  const scroll = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [words, setWords] = useState(false);
  const [disclosed, setDisclosed] = useState(false);
  const [purposeId, setPurposeId] = useState("welcome-everyone");
  const media = useRef(new MediaController());
  const current = useRef<Session | undefined>(undefined);
  const active = useRef(false);
  const attempt = useRef(0);
  const selected = content?.purposes.find(
    (p) =>
      p.purpose_id ===
      (view === "practice" ? (saved?.purpose_id ?? purposeId) : purposeId),
  );
  const currentRetry = saved?.retries.at(-1);
  const answerCount =
    (saved?.phase === "retry"
      ? currentRetry?.answers.length
      : saved?.answers.length) ?? 0;
  const detailedRetry = saved?.retries.find((r) => r.id === retryDetails);
  useEffect(() => {
    scroll.current?.scrollTo(0, 0);
    const heading = scroll.current?.querySelector("h1");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  }, [view]);
  useEffect(() => {
    setReviewTab("takeaway");
  }, [saved?.id, saved?.lifecycle]);

  function navigate(next: View) {
    stop();
    setError("");
    setView(next);
  }

  function back() {
    if (view === "practice") void home();
    else
      navigate(
        view === "expression"
          ? "purposes"
          : view === "privacy"
            ? privacyReturn
            : "home",
      );
  }

  const reconcile = useCallback((next: Session) => {
    const previous = current.current;
    if (
      previous &&
      previous.id === next.id &&
      previous.revision > next.revision
    )
      return;
    if (
      active.current &&
      current.current?.connection_epoch !== next.connection_epoch
    ) {
      media.current.stop();
      active.current = false;
      setConnected(false);
    }
    current.current = next;
    setSaved(next);
    media.current.sync(next);
    if (next.lifecycle !== "in_progress") {
      active.current = false;
      setConnected(false);
    }
  }, []);

  const refreshList = useCallback(
    async () => setRecent(await api<Session[]>("/sessions")),
    [],
  );
  useEffect(() => {
    let canceled = false;
    void (async () => {
      try {
        await api("/guest", {});
        const [data, sessions] = await Promise.all([
          api<Content>("/content"),
          api<Session[]>("/sessions"),
        ]);
        if (canceled) return;
        setContent(data);
        setRecent(sessions);
        const identifier = new URL(location.href).searchParams.get("session");
        if (identifier) {
          reconcile(await api<Session>(`/sessions/${identifier}`));
          setView("practice");
        }
      } catch (e) {
        if (!canceled) setError(message(e));
      }
    })();
    return () => {
      canceled = true;
    };
  }, [reconcile]);

  const stop = useCallback(() => {
    attempt.current++;
    active.current = false;
    media.current.stop();
    setConnected(false);
  }, []);

  const pause = useCallback(async () => {
    stop();
    const session = current.current;
    if (!session || session.lifecycle !== "in_progress") return;
    try {
      const result = await sendCommand(session, "pause");
      reconcile(result);
    } catch {
      await api<Session>(`/sessions/${session.id}`)
        .then(reconcile)
        .catch(() => {});
    }
  }, [reconcile, stop]);

  useEffect(() => {
    media.current.onLoss = () => {
      void pause();
      setError("The connection ended. Resume when you’re ready.");
    };
    media.current.onAudioError = () => {
      void pause();
      setError(
        "Audio couldn’t play. Resume to try again, or open the saved words.",
      );
    };
    const hidden = () => {
      if (document.hidden) void pause();
    };
    const unload = () => {
      media.current.stop();
    };
    document.addEventListener("visibilitychange", hidden);
    window.addEventListener("pagehide", unload);
    return () => {
      document.removeEventListener("visibilitychange", hidden);
      window.removeEventListener("pagehide", unload);
      media.current.stop();
    };
  }, [pause]);

  useEffect(() => {
    if (!saved || view !== "practice") return;
    const identifier = saved.id;
    const events = new EventSource(`/api/sessions/${identifier}/events`);
    events.addEventListener("snapshot", (e) => {
      const event = JSON.parse((e as MessageEvent).data);
      if (event.session_id === identifier && event.schema_version === 1)
        reconcile(event.snapshot);
    });
    events.addEventListener("unavailable", () => {
      stop();
      setError("This temporary session is no longer available.");
      events.close();
    });
    events.onerror = () => {
      if (active.current) {
        void pause();
        setError("The connection ended. Your accepted answers are saved.");
      }
    };
    return () => events.close();
  }, [saved?.id, view, reconcile, pause, stop]);

  useEffect(() => {
    if (!connected || !saved) return;
    const timer = window.setInterval(() => {
      if (!active.current || document.hidden) return;
      void api(`/sessions/${saved.id}/heartbeat`, {
        connection_epoch: saved.connection_epoch,
      }).catch(() => void pause());
    }, 5000);
    return () => clearInterval(timer);
  }, [connected, saved?.id, saved?.connection_epoch, pause]);

  async function start(source?: Session) {
    media.current.unlock();
    stop();
    setBusy(true);
    setError("");
    const ticket = attempt.current;
    try {
      let session = source ? undefined : current.current;
      if (!session) {
        session = await api<Session>("/sessions", {
          purpose_id: source?.purpose_id ?? purposeId,
          command_id: id(),
          source_session_id: source?.id,
        });
        if (ticket !== attempt.current) return;
        reconcile(session);
        history.replaceState(null, "", `?session=${session.id}`);
      }
      setView("practice");
      const connection = await api<Connection>(
        `/sessions/${session.id}/connect`,
        {},
      );
      if (ticket !== attempt.current) return;
      reconcile(connection.session);
      active.current = true;
      setConnected(true);
      await media.current.connect(connection);
      if (ticket !== attempt.current) {
        media.current.stop();
        return;
      }
      reconcile(await api<Session>(`/sessions/${session.id}`));
    } catch (e) {
      await pause();
      setError(
        e instanceof DOMException && e.name === "NotAllowedError"
          ? "Microphone access is off. Allow microphone access in your browser, then Resume."
          : message(e),
      );
    } finally {
      setBusy(false);
    }
  }

  async function control(
    type: Command["type"],
    options: Pick<Command, "expression_id" | "target_note_id"> = {},
  ) {
    const session = current.current;
    if (!session) return;
    if (type === "pause" || type === "finish" || type === "hint") stop();
    if (type === "hint") media.current.unlock();
    if (
      [
        "mute",
        "replay",
        "continue_answer",
        "focused_retry",
        "expression",
      ].includes(type)
    )
      media.current.suspendCapture(
        ["replay", "focused_retry", "expression"].includes(type),
        type === "mute",
      );
    setBusy(true);
    setError("");
    const ticket = attempt.current;
    try {
      const result = await sendCommand(session, type, options);
      if (ticket !== attempt.current) return;
      media.current.releaseHold();
      reconcile(result);
      if (type === "hint" && result.helper?.status === "ready")
        void media.current
          .review(result.id, result.helper.id)
          .catch(() =>
            setError("The hint is ready below, but audio is unavailable."),
          );
    } catch (e) {
      if (ticket !== attempt.current) return;
      await pause();
      await api<Session>(`/sessions/${session.id}`)
        .then(reconcile)
        .catch(() => {});
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  async function home() {
    await pause();
    setView("home");
    setSaved(undefined);
    current.current = undefined;
    setError("");
    setWords(false);
    history.replaceState(null, "", "/");
    await refreshList().catch((e) => setError(message(e)));
  }

  async function review(session: Session) {
    stop();
    reconcile(await api<Session>(`/sessions/${session.id}`));
    setView("practice");
    setError("");
    history.replaceState(null, "", `?session=${session.id}`);
  }

  const completed = saved?.lifecycle === "completed";
  const coaching = saved?.phase === "coaching" || completed;
  const live = connected && saved?.lifecycle === "in_progress";
  const status = !live
    ? completed
      ? "Practice saved"
      : "Ready when you are"
    : saved?.capture_muted && saved.substate === "ready"
      ? "Microphone off"
      : saved?.assessment.status === "unavailable" ||
          currentRetry?.assessment.status === "unavailable"
        ? "Coaching is unavailable"
        : statuses[saved?.substate ?? "connecting"];

  return (
    <main
      className={`portrait screen-${view}${coaching ? " is-coaching" : ""}${completed ? " is-completed" : ""}`}
    >
      <header className="app-header">
        {view !== "home" ? (
          <button
            className="icon-button"
            aria-label={
              view === "practice" || view === "purposes" || view === "recent"
                ? "Back to conversations"
                : view === "expression"
                  ? "Back to purposes"
                  : "Back"
            }
            onClick={back}
          >
            <Icon name="arrow-left" />
          </button>
        ) : null}
        <span className="app-title">Workplace English</span>
      </header>
      <div className="scroll-area" ref={scroll}>
        {error && (
          <div role="alert" className="error">
            <p>{error}</p>
            <button onClick={() => setError("")} aria-label="Dismiss message">
              <Icon name="x" />
            </button>
          </div>
        )}
        {!content && !error && (
          <p className="loading" role="status">
            Getting things ready…
          </p>
        )}
        {view === "privacy" ? (
          <section className="privacy">
            <h1>Your words, handled with care.</h1>
            <p>
              Your microphone audio goes through LiveKit Cloud and Deepgram
              Nova-3 for transcription. Google Gemini generates conversation and
              wording feedback through LiveKit Inference. Cartesia Sonic-3
              generates Alex’s voice.
            </p>
            <p>
              The application saves text and feedback temporarily, for up to 24
              hours after eligible practice activity. It does not save learner
              recordings. LiveKit Inference documents zero data retention; agent
              session recording is disabled.
            </p>
            <p>
              Delete removes this application’s session content. It does not
              operate external providers’ deletion systems.
            </p>
            <a
              href="https://docs.livekit.io/agents/models/inference/"
              target="_blank"
              rel="noreferrer"
            >
              LiveKit’s data policy
            </a>
          </section>
        ) : view === "home" ? (
          content && (
            <ScenarioCards
              select={(scenarioId) => {
                setPurposeId(
                  content.purposes.find((p) => p.scenario_id === scenarioId)!
                    .purpose_id,
                );
                navigate("purposes");
              }}
            />
          )
        ) : view === "purposes" ? (
          content &&
          selected && (
            <PurposePicker
              content={content}
              scenarioId={selected.scenario_id}
              select={(next) => {
                setPurposeId(next);
                navigate("expression");
              }}
            />
          )
        ) : view === "expression" ? (
          content && (
            <ExpressionPreview
              key={purposeId}
              content={content}
              selectedId={purposeId}
              stop={() => media.current.stop()}
              speak={(part) => {
                media.current.unlock();
                void media.current
                  .expression(purposeId, part)
                  .catch(() =>
                    setError(
                      "Audio is unavailable. You can still explore the expressions.",
                    ),
                  );
              }}
            />
          )
        ) : view === "recent" ? (
          <section className="recent">
            <h1>
              Recent sessions
              <span>
                Your practice in this browser · saved for up to 24 hours
              </span>
            </h1>
            {recent.length === 0 ? (
              <p>
                No sessions yet. Start a conversation to save your practice
                here.
              </p>
            ) : (
              recent.map((session) => (
                <div className="recent-row" key={session.id}>
                  <button
                    onClick={() =>
                      void review(session).catch((e) => setError(message(e)))
                    }
                  >
                    <span>
                      {
                        content?.purposes.find(
                          (p) => p.purpose_id === session.purpose_id,
                        )?.title
                      }
                      <small>
                        {session.lifecycle === "completed"
                          ? "Review"
                          : "Resume"}{" "}
                        · {session.answers.length} saved{" "}
                        {session.answers.length === 1 ? "answer" : "answers"}
                      </small>
                      <time
                        dateTime={new Date(
                          session.last_practice_at * 1000,
                        ).toISOString()}
                      >
                        {new Intl.DateTimeFormat(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                        }).format(session.last_practice_at * 1000)}
                      </time>
                    </span>
                    <Icon name="caret-right" />
                  </button>
                  <button
                    className="delete"
                    aria-label="Delete session"
                    onClick={() =>
                      void api(`/sessions/${session.id}`, undefined, "DELETE")
                        .then(refreshList)
                        .catch((e) => setError(message(e)))
                    }
                  >
                    <Icon name="x" />
                  </button>
                </div>
              ))
            )}
          </section>
        ) : saved ? (
          <>
            <div className="practice-heading">
              <p className="eyebrow">
                {scenarios.find((s) => s.id === selected?.scenario_id)?.title}
              </p>
              <h1>
                {completed
                  ? "Take it into your day."
                  : coaching
                    ? "A little more natural."
                    : saved.phase === "retry"
                      ? "Try a small change."
                      : selected?.title}
              </h1>
              <div className="progress">
                <span>
                  {completed
                    ? "Your takeaway"
                    : coaching
                      ? "Coaching"
                      : saved.phase === "retry"
                        ? "Focused retry"
                        : "Speaking practice"}
                </span>
                <span>
                  {`${answerCount} ${answerCount === 1 ? "answer" : "answers"} saved`}
                </span>
              </div>
            </div>
            {completed && saved.assessment.result && (
              <nav className="review-tabs" aria-label="Saved practice">
                <button
                  aria-pressed={reviewTab === "takeaway"}
                  onClick={() => setReviewTab("takeaway")}
                >
                  Takeaway
                </button>
                <button
                  aria-pressed={reviewTab === "feedback"}
                  onClick={() => setReviewTab("feedback")}
                >
                  Feedback & scores
                </button>
              </nav>
            )}
            {!coaching && (
              <div className="context-note">
                <Icon name="users-three" />
                <p>
                  {(saved.phase === "retry"
                    ? currentRetry?.situation
                    : saved.situation) ?? selected?.preset_situation}
                </p>
              </div>
            )}
            {!completed && (
              <section
                className={`voice-stage ${live && saved.substate === "speaking" ? "speaking" : ""}`}
                aria-live="polite"
              >
                <div className="voice-orb" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
                <h2>{status}</h2>
                <p>
                  {!live
                    ? "Start or resume to turn on your microphone."
                    : saved.substate === "listening"
                      ? saved.phase === "coaching"
                        ? "Ask about your wording, or try the suggestion below."
                        : "Take your time. Alex is listening."
                      : saved.substate === "speaking"
                        ? "Listen to Alex. Your microphone is off while he speaks."
                        : saved.substate === "opening" ||
                            saved.substate === "thinking"
                          ? "Listen first, then answer when it’s your turn."
                          : saved.substate === "capped"
                            ? "You reached the two-minute answer limit."
                            : "A short conversation with Alex."}
                </p>
              </section>
            )}
            {live && saved.input?.cue_shown && saved.substate !== "capped" && (
              <p className="cue" role="status">
                Wrap up your answer when you’re ready.
              </p>
            )}
            {saved.notice && <p className="notice">{saved.notice}</p>}
            {live && (
              <div className="control-row">
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() =>
                    void control(saved.capture_muted ? "unmute" : "mute")
                  }
                >
                  {saved.capture_muted ? "Unmute" : "Mute"}
                </button>
                <button
                  className="text-button"
                  disabled={busy || !saved.messages.length}
                  onClick={() => void control("replay")}
                >
                  Hear Alex
                </button>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => void control("hint")}
                >
                  Hint
                </button>
                {saved.phase === "roleplay" &&
                  saved.answers.length > 0 &&
                  saved.substate === "listening" && (
                    <button
                      className="text-button"
                      disabled={
                        busy || saved.answers.at(-1)!.capture_seconds >= 120
                      }
                      onClick={() => void control("continue_answer")}
                    >
                      I wasn’t finished
                    </button>
                  )}
              </div>
            )}
            {saved.helper && saved.lifecycle === "paused" && (
              <section className="context-note">
                <div>
                  <strong>A hint for you</strong>
                  <p>
                    {saved.helper.text ??
                      (saved.helper.status === "unavailable"
                        ? "The hint couldn’t finish. Try again when ready."
                        : "Preparing a short hint…")}
                  </p>
                  {saved.helper.status === "unavailable" && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => void control("retry_operation")}
                    >
                      Retry hint
                    </button>
                  )}
                  {!live && (
                    <button
                      className="text-button"
                      onClick={() => media.current.stop()}
                    >
                      Stop audio
                    </button>
                  )}
                </div>
              </section>
            )}
            {coaching &&
              (!completed ||
                !saved.assessment.result ||
                reviewTab === "feedback") && (
                <Feedback
                  session={saved}
                  retry={() => void control("retry_operation")}
                  reminder={selected?.expression ?? ""}
                />
              )}
            {saved.phase === "coaching" &&
              !completed &&
              saved.assessment.result && (
                <button
                  className="secondary full"
                  disabled={busy || !live}
                  onClick={() => void control("focused_retry")}
                >
                  Try this suggestion · 1–2 answers
                </button>
              )}
            {saved.phase === "retry" && currentRetry && (
              <section className="coaching-note">
                <p className="eyebrow">Your focus</p>
                <p>{currentRetry.target}</p>
                <small>Your original scores stay saved.</small>
              </section>
            )}
            {saved.retries
              .filter((r) => r.assessment.status !== "none")
              .map((retry, index) => (
                <button
                  className="retry-summary"
                  key={retry.id}
                  onClick={() => setRetryDetails(retry.id)}
                >
                  <span>Focused retry {index + 1} · Based on your words</span>
                  <Icon name="caret-right" />
                </button>
              ))}
            <Sheet
              open={!!detailedRetry}
              title="Focused retry feedback"
              close={() => setRetryDetails(undefined)}
            >
              {detailedRetry && (
                <>
                  <p>
                    {detailedRetry.assessment.result?.observation ??
                      (detailedRetry.assessment.status === "unavailable"
                        ? "This retry’s feedback is unavailable. Your retry answers are saved."
                        : "Looking at how you used the suggestion…")}
                  </p>
                  {detailedRetry.assessment.result && (
                    <>
                      <p>{detailedRetry.assessment.result.suggestion}</p>
                      <blockquote>
                        {detailedRetry.assessment.result.modeled_example}
                      </blockquote>
                      <h3>Your retry evidence</h3>
                      {detailedRetry.assessment.result.evidence.map((e, i) => (
                        <blockquote key={i}>
                          {e.quote && <q>{e.quote}</q>}
                          <p>{e.observation}</p>
                        </blockquote>
                      ))}
                    </>
                  )}
                  {detailedRetry.assessment.status === "unavailable" && (
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => void control("retry_operation")}
                    >
                      Retry feedback
                    </button>
                  )}
                </>
              )}
            </Sheet>
            {live && selected && (
              <>
                <button
                  className="text-button practice-expression"
                  onClick={() => setPracticeExpression(true)}
                >
                  <Icon name="lightbulb" /> An expression to try
                </button>
                <Sheet
                  open={practiceExpression}
                  title="An expression to try"
                  close={() => setPracticeExpression(false)}
                >
                  <blockquote>{selected.expression}</blockquote>
                  <p>{selected.explanation}</p>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => {
                      setPracticeExpression(false);
                      void control("expression", {
                        expression_id: "expression",
                      });
                    }}
                  >
                    Hear the expression
                  </button>
                </Sheet>
              </>
            )}
            {completed && saved.answers.length === 0 && (
              <button
                className="secondary full"
                onClick={() => {
                  media.current.unlock();
                  void media.current
                    .review(saved.id, "reminder")
                    .catch(() =>
                      setError(
                        "Audio is unavailable. The expression is still here.",
                      ),
                    );
                }}
              >
                Listen to the expression reminder
              </button>
            )}
            {completed && saved.answers.length === 0 && (
              <button
                className="text-button full"
                onClick={() => media.current.stop()}
              >
                Stop audio
              </button>
            )}
            {completed &&
              saved.assessment.result &&
              reviewTab === "takeaway" && (
                <section className="takeaway">
                  <p className="eyebrow">Take this with you</p>
                  <blockquote>{saved.assessment.result.takeaway}</blockquote>
                  <button
                    className="secondary"
                    onClick={() => {
                      media.current.unlock();
                      void media.current
                        .review(saved.id, "takeaway")
                        .catch(() =>
                          setError(
                            "Playback is unavailable. Your saved words are still here.",
                          ),
                        );
                    }}
                  >
                    <Icon name="speaker-high" />
                    Listen to your takeaway
                  </button>
                  <button
                    className="text-button"
                    onClick={() => media.current.stop()}
                  >
                    Stop audio
                  </button>
                </section>
              )}
            {saved.messages.length > 0 && (
              <div className="transcript">
                <button
                  className="text-button"
                  aria-expanded={words}
                  onClick={() => setWords(!words)}
                >
                  <Icon name="text-align-left" />
                  {words ? "Hide words" : "Show words"}
                </button>
                <Sheet
                  open={words}
                  title="Conversation words"
                  close={() => setWords(false)}
                >
                  <div>
                    {saved.messages.map((m) => (
                      <div key={m.id}>
                        <p>
                          <strong>Alex</strong>{" "}
                          <small>
                            {m.delivery === "completed"
                              ? "Playback completed"
                              : m.delivery}
                          </small>
                        </p>
                        <p>{m.text}</p>
                        {[
                          ...saved.answers,
                          ...saved.retries.flatMap((r) => r.answers),
                        ]
                          .filter((a) => a.question_id === m.id)
                          .map((a) => (
                            <div className="your-words" key={a.id}>
                              <strong>You · saved answer</strong>
                              <p>{a.transcript.text}</p>
                            </div>
                          ))}
                      </div>
                    ))}
                  </div>
                </Sheet>
              </div>
            )}
            <p className="retention">
              Available for up to 24 hours after practice. No learner recordings
              saved.
            </p>
          </>
        ) : null}
      </div>
      {view === "expression" && (
        <footer className="entry-controls">
          <label className="entry-disclosure">
            <input
              type="checkbox"
              checked={disclosed}
              onChange={(e) => setDisclosed(e.target.checked)}
            />
            <span>
              I understand my speech is processed by LiveKit and its model
              providers. History is temporary. Alex’s voice is AI-generated.
            </span>
          </label>
          <button
            className="primary full"
            disabled={!disclosed || busy || !content}
            onClick={() => void start()}
          >
            <Icon name="microphone" />
            {busy ? "Connecting…" : "Start practice"}
            <Icon name="arrow-right" />
          </button>
          <button
            className="privacy-link"
            onClick={() => {
              setPrivacyReturn("expression");
              navigate("privacy");
            }}
          >
            How your data is handled
          </button>
        </footer>
      )}
      {["home", "purposes", "recent"].includes(view) && (
        <nav className="app-tabs" aria-label="Main navigation">
          <button
            aria-current={view !== "recent" ? "page" : undefined}
            onClick={() => navigate("home")}
          >
            <Icon name="chats" />
            <span>Conversations</span>
          </button>
          <button
            aria-current={view === "recent" ? "page" : undefined}
            onClick={() => {
              navigate("recent");
              void refreshList().catch((e) => setError(message(e)));
            }}
          >
            <Icon name="arrow-counter-clockwise" />
            <span>Recent sessions</span>
          </button>
        </nav>
      )}
      {view === "practice" && saved && (
        <footer className="controls">
          {completed ? (
            <>
              <button
                className="primary full"
                disabled={busy}
                onClick={() => void start(saved)}
              >
                {busy ? "Connecting…" : "Practice again"}
                <Icon name="arrow-right" />
              </button>
              <button className="text-button full" onClick={() => void home()}>
                Back to conversations
              </button>
            </>
          ) : (
            <>
              {live && saved.substate === "capped" ? (
                <div className="control-row">
                  <button
                    className="primary"
                    disabled={
                      busy ||
                      saved.input?.status !== "awaiting_limit_confirmation"
                    }
                    onClick={() => void control("use_answer")}
                  >
                    Use this answer
                  </button>
                  <button
                    className="secondary"
                    disabled={
                      busy ||
                      saved.input?.status !== "awaiting_limit_confirmation"
                    }
                    onClick={() => void control("try_again")}
                  >
                    Try again
                  </button>
                </div>
              ) : !live ? (
                <button
                  className="primary full"
                  disabled={busy}
                  onClick={() => void start()}
                >
                  <Icon name="microphone" />
                  {busy ? "Connecting…" : "Resume practice"}
                </button>
              ) : (
                <div className="control-row">
                  <button
                    className="secondary"
                    onClick={() => void control("pause")}
                  >
                    <Icon name="pause" />
                    Pause
                  </button>
                  {saved.substate === "unavailable" ? (
                    <button
                      className="primary"
                      disabled={busy}
                      onClick={() => void control("retry_operation")}
                    >
                      Try voice again
                    </button>
                  ) : (
                    <button
                      className="primary"
                      disabled={
                        busy ||
                        saved.substate !== "listening" ||
                        saved.input?.status !== "open"
                      }
                      onClick={() => void control("done")}
                    >
                      <Icon name="check" />
                      I’m done
                    </button>
                  )}
                </div>
              )}
              <button
                className="finish text-button"
                disabled={busy}
                onClick={() => void control("finish")}
              >
                Finish practice
              </button>
            </>
          )}
        </footer>
      )}
    </main>
  );
}
