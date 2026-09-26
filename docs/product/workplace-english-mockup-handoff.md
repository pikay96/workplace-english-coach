# Workplace English tutor — mockup and specification handoff

Date: 2026-09-26

Status: revision 02 of the clickable mockup is complete for discussion. Product and technical specifications are the next step; the production application has not been implemented.

**Product specification:** The [product specification for review](workplace-english-product-spec.md) records the subsequent product decisions: intermediate learners, mobile web with guest access, all seven purposes, adaptive 3–5-turn exchanges, four exchange-level scores, focused 1–2-turn retries, and temporary Recent sessions with Resume/Review. Its interaction and lifecycle requirements supersede conflicting mockup behavior. Technical design and implementation remain separate next steps.

Read this document first in the next session, together with the [original assignment](../requirements/general-take-home-project.md). The [brainstorm](workplace-english-brainstorm.md) preserves the earlier product reasoning; the [mockup direction](../design/workplace-english/mockup-direction.md) records detailed visual and interaction choices.

## 1. Product intent and decisions

Help non-native English speakers find suitable workplace expressions more quickly and use them comfortably in conversation. The learner often knows the intended meaning but cannot recall wording readily enough. They also want to sound warm, natural, and appropriate, including making colleagues feel welcome.

The organizing model is **scenario → communication purpose → expressions and reasoning → speaking practice**. Teach why an expression works, then help the learner recall and adapt it. Normal thinking pauses are welcome.

| Area | Established direction | Still a proposal or open decision |
| --- | --- | --- |
| Subject | Workplace English | Exact proficiency level, first language, region, and career stage |
| Scenarios | Hosting a meeting, casual talk, one-on-one | Final curriculum size and content authoring approach |
| Audience and form | Primarily phone users; portrait, touch-friendly experience | Mobile web versus native app |
| Teaching | Expressions paired with communicative purpose and reasoning, followed by practice | Exercise length and progression |
| Voice | The user explicitly said voice is always primary; the tutor must respond and coach aloud | Production voice, speech stack, and detailed turn-taking behavior |
| Text | Secondary support for expressing and understanding meaning | Translation/language support and caption preferences |
| Assessment | The user explicitly requested several scoring dimensions after the learner speaks | Exact dimensions, scale, rubric, evidence thresholds, and timing within longer conversations |
| Deliverable from this session | User selected a clickable phone mockup with precise typography and PNG previews | The mockup is a design reference, not a selected application architecture |

The user preferred moving into the overall experience rather than continuing to investigate individual workplace situations. The next session should resolve material product and technical decisions without reopening this established direction unnecessarily.

## 2. How the design evolved

**Revision 01** established six screens: scenario selection, expression exploration, voice practice, a hint sheet, coaching/retry, and a takeaway. Practice used a prominent text roleplay card and simulated voice states. Feedback offered one useful suggestion without numerical scores.

The user then clarified:

> Better the tutor would help give scores with several dimensions after user speaks, like fluency, native, etc. Also, the tutor should also be able to respond user with voice, right? Voice is always primary in this product, while text can be the secondary to help express meanings.

**Revision 02, the current mockup,** makes the active speaker, waveform, and audio controls central. Tutor setup, roleplay replies, hints, coaching, expressions, and takeaways have audible playback. Conversation words and written coaching are initially collapsed. Feedback combines spoken coaching with four visible example scores and a retry.

This clarification supersedes the earlier text-heavy practice layout and score-free feedback. The specific four dimensions and 1–5 scale are the design's interpretation of the request, not separately finalized requirements.

The provisional name is **Good Company**. Its calm editorial style uses warm ivory, charcoal, muted sage, Newsreader for headings and memorable expressions, and Plus Jakarta Sans for controls and body text. Dark recording-studio and colorful lesson-path directions were considered; the current treatment supports a welcoming workplace practice companion. Branding, tutor name **Alex**, palette, and typography remain proposals.

The design drew on the brainstorming, mobile mockup, minimalist UI, and high-end visual design skills. The broader frontend taste skill excluded multi-step product UI and was not used as a page template. Built-in image generation was unavailable, so the user chose the clickable HTML/CSS/JavaScript alternative. PNG previews were rendered from the prototype.

## 3. Current experience

The reference journey is **Hosting a meeting → welcome everyone → practice → coaching and scores → retry → takeaway**.

| Screen | Experience |
| --- | --- |
| Choose a conversation | “What's coming up?” offers hosting a meeting, casual talk, and one-on-one. |
| Explore an expression | Select a purpose, see a useful phrase, learn why it works, hear it, and start practice. |
| Practice | Alex sets the situation aloud and plays the other person. Active-speaker status and audio controls lead; **Show words** and **View transcript** provide optional text. |
| Hint | A bottom sheet stops roleplay playback and pauses the simulated microphone. **Hear a hint** offers a spoken starter, supported by short phrases. |
| Coaching and retry | Alex becomes “your coach.” Spoken feedback leads, followed by four scores and one focused next step. **Read coaching notes** is collapsed initially; **Try that again** starts another attempt. |
| Takeaway | Hear and see an expression to reuse and the pattern behind it, then return to conversations. Persistent saving is not implemented or decided. |

There are seven purpose examples across the three scenarios: welcome, set the agenda, wrap up; start a chat, follow up; share progress, ask for support. These establish reusable content structure rather than a large curriculum.

### Reference teaching example

Main expression:

> Good to see everyone. Thanks for making the time today.

Why it works: acknowledge the people and appreciate their time before getting down to work. A more casual alternative is “Hey everyone, glad you could make it.”

The sample exchange:

- **Alex:** “Hi! I think everyone's here. Shall we start?”
- **Prepared learner answer:** “Hello, everyone. Today we'll talk about the project timeline.”
- **Alex, in character:** “Sounds good. What would you like us to decide today?”
- **Alex, coaching:** “Your purpose was clear. Add a welcome before the agenda to acknowledge the group. Try: Good to see everyone. Thanks for making the time today.”

The takeaway pattern is **acknowledge people → appreciate their time → introduce the purpose**. The learner should be able to adapt that pattern to their own relationships and personality.

### Voice behavior and feedback

Current controls include **Start talking with Alex**, **Speak now**, **Pause/Resume**, **Mute/Unmute**, **Hint**, **Hear Alex**, and **Finish**. Speaking can interrupt tutor playback; help pauses the exchange. Ready, connecting, listening, tutor speaking, thinking, paused, microphone unavailable, and connection lost are represented as designed states.

The short demonstration follows **prepared learner answer → in-character tutor reply → spoken coaching and scores**. Longer roleplay remains an open product decision. A proposed approach is to assess completed responses quietly and deliver spoken coaching at natural breaks or when requested, avoiding interruption of an unfinished learner turn.

| Proposed dimension | What it describes | Initial example score |
| --- | --- | --- |
| Fluency | Flow, phrasing, and comfortable pacing | 3/5 |
| Pronunciation | Intelligibility, sounds, and stress | 4/5 |
| Naturalness | Idiomatic, everyday wording | 3/5 |
| Workplace tone | Warmth and directness suited to the situation | 3/5 |

“Naturalness” interprets the user's suggestion of “native.” Pronunciation concerns understandability; accent identity is not a scoring criterion. Each score opens an explanation with example scale anchors. There is no headline aggregate grade. Spoken coaching gives one useful change rather than reading every number aloud.

Retry uses a different prepared answer and coaching titled **Make it your own**. Its illustrative naturalness and tone scores rise to 4/5. These increases are scripted, not evidence of actual improvement or a required scoring rule.

For real assessment, fluency and pronunciation need speech audio; a transcript alone is insufficient. The proposed fallback is **Not enough speech** for dimensions without adequate evidence. The mockup has no calibrated rubric, selected evaluator, or established assessment accuracy.

## 4. What exists and what is simulated

The artifact is a working static design prototype with local fonts, icons, and **63 prepared WAV clips**. Windows Microsoft David voices the tutor and Microsoft Zira voices sample learner answers. These are preview voices, not production provider choices. No image-generation or voice API was used.

Playback is real; microphone capture, conversation intelligence, scoring, and connection states are simulated. There is no live speech recognition, LiveKit agent, Redis integration, account system, persistence, or Docker application. The UI labels prepared audio and example scores. Prototype scripts should not be treated as the production state model.

Recorded verification covered actual playback, pause/resume, interruption, hint cancellation, learner/reply/coaching sequencing, distinct retry content, score explanations, optional written feedback, stopping audio on navigation, and playback failure handling. Responsive layouts were checked at 390×844, 375×667, and 320×640; all 63 WAV files were validated as nonempty mono audio. This verifies prototype behavior, not live-agent latency, speech recognition, or scoring validity.

The reference phone viewport is 390×844 CSS pixels. Six primary screens and two recovery states have separate 924×1832 PNG exports including the device frame.

### Review artifacts

- [Prototype README and complete artifact index](../design/workplace-english/README.md)
- [Detailed visual tokens, copy, states, and review criteria](../design/workplace-english/mockup-direction.md)
- [Current voice and scoring overview](../design/workplace-english/previews/voice-flow.png)
- [Choose → explore → practice overview](../design/workplace-english/previews/primary-flow.png)
- [Hint → feedback → takeaway overview](../design/workplace-english/previews/supporting-flow.png)
- [Prototype entry point](../design/workplace-english/index.html), [scenario content](../design/workplace-english/scenario-content.js), and [score definitions/audio wording](../design/workplace-english/voice-content.js)
- [Earlier learner-interest research](../research/voice-tutor-learner-interest.md); these are interest signals, not validation of this exact product.

To open the mockup from the repository root:

```powershell
python -m http.server 4173 --bind 127.0.0.1 --directory docs/design/workplace-english
```

Then visit [the home screen](http://127.0.0.1:4173/?v=2#home). Follow **Hosting a meeting → Practice this opening → Start practice → Start talking with Alex → Play sample answer**. The sample control advances prepared audio; it does not record the reviewer.

## 5. Assignment constraints for the specification

The [original assignment](../requirements/general-take-home-project.md) remains authoritative:

- Real-time voice tutor using **LiveKit**, with a backend and frontend.
- **Redis** as the backing state store for conversations.
- Runnable after clone using **Docker and Docker Compose**, with configuration and secrets from a root `.env` and a complete `.env.example`.
- Clear separation of session management, conversation handling, and the voice/AI layer.
- README explaining architecture, decisions, tradeoffs, and changes needed for **10,000 concurrent sessions**.
- Exact assignment text in `PROMPT.md`; actual AI tools, models, harnesses, and workflow in `workflow.md`.
- A demonstration video of the interface and functioning agent.
- Submission as a repository zip **including `.git`**.

The assignment's expected time is **two hours**, prioritizing working software. The specification should explicitly scope the smallest runnable experience and defer extensions. Phone mockups do not require a native application. Framework, backend language, providers, Redis schema, and deployment approach remain undecided.

## 6. Decisions for the next session

Create a product specification and a technical specification, using the current mockup as a concrete reference. Resolve these questions before planning implementation:

| Area | Decision to make |
| --- | --- |
| Exercise model | Short guided attempts, continuous roleplay, or both? When are scores shown and spoken coaching delivered? |
| Learner and content | Target proficiency and language support; required scenarios/purposes for the take-home; how much personalization is necessary? |
| Assessment | Final dimensions and scale; evidence and minimum sample requirements; rubric and calibration; treatment of unclear or interrupted input; what a retry should demonstrate. |
| Conversation behavior | How a turn ends; tolerance for thinking pauses; interruption; explicit roleplay/coaching transitions; precise pause, mute, replay, help, finish, and resume semantics. |
| Delivery and providers | Frontend platform, backend stack, LiveKit integration, speech/LLM/assessment providers, latency budget, and behavior when a provider is slow or unavailable. |
| State and recovery | Ownership of session/turn/assessment state; Redis records and TTLs; reconnect, cancellation, retry, and prevention of duplicate or stale events. |
| Data lifecycle | Whether audio is retained; transcript, score, and session retention/deletion; anonymous sessions versus any identity requirement. |
| Acceptance and scope | Minimum end-to-end voice behavior, meaningful assessment checks, failure recovery, Docker Compose startup, and required submission materials. |

Suggested order: settle the exercise and feedback loop; write product acceptance criteria; choose the simplest architecture satisfying them and the assignment; then define implementation milestones. Features such as saved expressions, session history, accounts, streaks, and a larger curriculum are not required by the current mockup.

### Suggested opening prompt

> Read `docs/product/workplace-english-mockup-handoff.md` and `docs/requirements/general-take-home-project.md`, then inspect the current mockup and its design notes. Help me write the product and technical specifications for this workplace English voice tutor. Preserve the agreed voice-first experience, supporting text, scenario-based expression learning, and multidimensional feedback. Distinguish user decisions from mockup proposals, resolve material open questions, and scope the smallest working LiveKit/Redis application that meets the Docker Compose take-home requirements. Produce the specifications and an implementation plan; do not start implementation yet.
