import type { Content } from "../api/client";

export const scenarios = [
  {
    id: "hosting-a-meeting",
    title: "Hosting a meeting",
    description: "Welcome, guide, and wrap up.",
    icon: "users-three",
  },
  {
    id: "one-on-one",
    title: "One-on-one",
    description: "Share progress. Ask with confidence.",
    icon: "chats",
  },
  {
    id: "casual-talk",
    title: "Casual talk",
    description: "Make room for a little connection.",
    icon: "coffee",
  },
];

export function ScenarioCards({ select }: { select: (id: string) => void }) {
  return (
    <>
      <section className="home-intro">
        <p className="eyebrow">English, out loud</p>
        <h1>
          A little practice.
          <br />
          <em>A better conversation.</em>
        </h1>
        <p>Where would you like to feel more at ease?</p>
      </section>
      <nav className="scenario-cards" aria-label="Conversation scenarios">
        {scenarios.map((scenario, index) => (
          <button
            className={`scenario-card scenario-card-${index + 1}`}
            key={scenario.id}
            aria-label={scenario.title}
            onClick={() => select(scenario.id)}
          >
            <span className="scenario-art" aria-hidden="true">
              <img src={`/assets/icons/${scenario.icon}.svg`} alt="" />
            </span>
            <span className="scenario-card-copy">
              <strong>{scenario.title}</strong>
              <span>{scenario.description}</span>
            </span>
            <img
              className="card-arrow icon"
              src="/assets/icons/arrow-right.svg"
              alt=""
            />
          </button>
        ))}
      </nav>
      <p className="entry-footnote">
        A short conversation. Something you can use today.
      </p>
    </>
  );
}

export function PurposePicker({
  content,
  scenarioId,
  select,
}: {
  content: Content;
  scenarioId: string;
  select: (id: string) => void;
}) {
  const scenario = scenarios.find((s) => s.id === scenarioId)!;
  return (
    <section className="purpose-picker">
      <p className="eyebrow">Choose your moment</p>
      <div className="scenario-heading">
        <img
          className="scenario-heading-icon"
          src={`/assets/icons/${scenario.icon}.svg`}
          alt=""
        />
        <h1>{scenario.title}</h1>
      </div>
      <p className="screen-description">What would you like to practice?</p>
      <div className="purpose-list" aria-label="Communication purposes">
        {content.purposes
          .filter((p) => p.scenario_id === scenarioId)
          .map((purpose) => (
            <button
              key={purpose.purpose_id}
              aria-label={purpose.title}
              onClick={() => select(purpose.purpose_id)}
            >
              <span>
                <strong>{purpose.title}</strong>
                <small>{purpose.expression}</small>
              </span>
              <img
                className="icon"
                src="/assets/icons/caret-right.svg"
                alt=""
              />
            </button>
          ))}
      </div>
      <div className="practice-note">
        <img className="icon" src="/assets/icons/microphone.svg" alt="" />
        <p>
          <strong>Make it your own.</strong>
          <br />
          Try 2–3 spoken answers with Alex, then get a little wording advice.
        </p>
      </div>
    </section>
  );
}

type ExpressionPart = "expression" | "alternative" | "example";

export function ExpressionPreview({
  content,
  selectedId,
  speak,
  stop,
}: {
  content: Content;
  selectedId: string;
  speak: (part: ExpressionPart) => void;
  stop: () => void;
}) {
  const selected = content.purposes.find((p) => p.purpose_id === selectedId)!;
  return (
    <section className="expression-screen">
      <p className="eyebrow">
        {scenarios.find((s) => s.id === selected.scenario_id)?.title}
      </p>
      <h1>{selected.title}</h1>
      <div className="expression-content">
        <h2 className="phrase-label">You can say</h2>
        <blockquote>{selected.expression}</blockquote>
        <p>{selected.explanation}</p>
        <div className="expression-audio">
          <button className="listen-button" onClick={() => speak("expression")}>
            <img className="icon" src="/assets/icons/speaker-high.svg" alt="" />
            Listen to the phrase
          </button>
          <button className="text-button" onClick={stop}>
            Stop audio
          </button>
        </div>
      </div>
      <div className="preview-disclosures">
        <details className="preview-details" name="practice-preview">
          <summary>
            <span>More examples</span>
            <img
              className="icon disclosure-chevron"
              src="/assets/icons/caret-right.svg"
              alt=""
            />
          </summary>
          <div className="preview-detail-body">
            <h3>You could also say</h3>
            <blockquote>{selected.alternative}</blockquote>
            <button
              className="listen-button"
              onClick={() => speak("alternative")}
            >
              <img
                className="icon"
                src="/assets/icons/speaker-high.svg"
                alt=""
              />
              Listen to this version
            </button>
            <h3>Here’s a full example</h3>
            <blockquote>{selected.example}</blockquote>
            <button className="listen-button" onClick={() => speak("example")}>
              <img
                className="icon"
                src="/assets/icons/speaker-high.svg"
                alt=""
              />
              Listen to the example
            </button>
          </div>
        </details>
        <details className="preview-details" name="practice-preview">
          <summary>
            <span>
              <img
                className="icon"
                src="/assets/icons/users-three.svg"
                alt=""
              />
              Your practice situation
            </span>
            <img
              className="icon disclosure-chevron"
              src="/assets/icons/caret-right.svg"
              alt=""
            />
          </summary>
          <div className="preview-detail-body">
            <p>{selected.preset_situation}</p>
            <p>
              <strong>Your role</strong>
              <br />
              {selected.learner_role}
            </p>
            <p>
              <strong>With Alex</strong>
              <br />
              {selected.tutor_role}
            </p>
            <p>Alex speaks first. When he finishes, it’s your turn.</p>
          </div>
        </details>
      </div>
    </section>
  );
}
