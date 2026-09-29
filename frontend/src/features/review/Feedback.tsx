import { useState } from "react";
import { Sheet } from "../Sheet";
import type { Dimension, Session } from "../../api/client";

const labels: Record<Dimension["status"], string> = {
  scored: "",
  not_enough_detail: "Not enough detail",
  transcript_unclear: "Transcript unclear",
  assessment_unavailable: "Assessment unavailable",
};

export function Feedback({
  session,
  retry,
  reminder,
}: {
  session: Session;
  retry: () => void;
  reminder: string;
}) {
  const [detail, setDetail] = useState<string>();
  const result = session.assessment.result;
  const dimension =
    detail === "naturalness" || detail === "workplace_tone"
      ? result?.dimensions[detail]
      : undefined;
  if (!result)
    return (
      <section className="feedback-state" aria-live="polite">
        <h2>
          {session.answers.length === 0
            ? "A phrase to take with you"
            : session.assessment.status === "unavailable"
              ? "Coaching is unavailable"
              : "Looking at your words"}
        </h2>
        <p>
          {session.answers.length === 0
            ? reminder
            : session.assessment.status === "unavailable"
              ? "Your accepted answers are saved. You can ask Alex to try the assessment again."
              : "Your answers are saved. Alex is preparing feedback on your wording."}
        </p>
        {session.answers.length === 0 && (
          <p>No answers saved. Keep this expression for next time.</p>
        )}
        {session.assessment.status === "unavailable" && (
          <button className="secondary" onClick={retry}>
            Try assessment again
          </button>
        )}
      </section>
    );
  return (
    <div className="feedback">
      <p className="eyebrow">Based on your words</p>
      <div className="dimensions">
        {Object.entries(result.dimensions).map(([key, dimension]) => (
          <button
            key={key}
            className="dimension"
            onClick={() => setDetail(key)}
          >
            <span>
              {key === "naturalness" ? "Naturalness" : "Workplace tone"}
            </span>
            {dimension.status === "scored" ? (
              <strong>
                {dimension.score}
                <small>/5</small>
              </strong>
            ) : (
              <b className="unscored">{labels[dimension.status]}</b>
            )}
            <span className="detail-link">
              View evidence <span aria-hidden="true">↗</span>
            </span>
          </button>
        ))}
      </div>
      <section className="coaching-note">
        <h3>One thing to try</h3>
        <p className="brief-text">{result.retry_priority.suggestion}</p>
        <blockquote className="brief-text">{result.modeled_example}</blockquote>
      </section>
      <button
        className="text-button coaching-details"
        onClick={() => setDetail("notes")}
      >
        Coaching notes <span aria-hidden="true">↗</span>
      </button>
      <Sheet
        open={!!detail}
        title={
          dimension
            ? detail === "naturalness"
              ? "Naturalness"
              : "Workplace tone"
            : "Coaching notes"
        }
        close={() => setDetail(undefined)}
      >
        {dimension ? (
          <>
            <p>{dimension.explanation}</p>
            {dimension.evidence.map((e, i) => (
              <blockquote key={i}>
                {e.quote && <q>{e.quote}</q>}
                <p>{e.observation}</p>
              </blockquote>
            ))}
          </>
        ) : (
          <>
            <h3>One thing to try</h3>
            <p>{result.retry_priority.suggestion}</p>
            <blockquote>{result.modeled_example}</blockquote>
            <p>{result.spoken_summary}</p>
            {[...result.strengths, ...result.issues].map((note) => (
              <section key={note.id}>
                <h3>{note.observation}</h3>
                <p>{note.suggestion}</p>
                <blockquote>{note.example}</blockquote>
                <p>{note.reason}</p>
                {note.evidence.map((e, index) => (
                  <blockquote key={index}>
                    {e.quote && <q>{e.quote}</q>}
                    <p>{e.observation}</p>
                  </blockquote>
                ))}
              </section>
            ))}
          </>
        )}
      </Sheet>
    </div>
  );
}
