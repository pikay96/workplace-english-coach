# Workplace English tutor — product specification

Date: 2026-09-26

Status: complete product draft for review. Product choices reflect the specification discussion; detailed controls, rubric anchors, and acceptance scenarios are included for written review. Implementation has not started.

## Sources and authority

- The [original assignment](../requirements/general-take-home-project.md) defines required delivery and technical constraints.
- The [brainstorm](workplace-english-brainstorm.md) records the learner's problem and initial product direction.
- The [mockup handoff](workplace-english-mockup-handoff.md) distinguishes established direction from design proposals.
- The [mockup direction](../design/workplace-english/mockup-direction.md) provides a concrete interaction and visual reference.
- The [domain glossary](../../CONTEXT.md) defines product terminology.

This specification supersedes conflicting mockup behavior. The mockup remains the visual reference; its prepared audio, scores, and connection simulation are not product implementation.

## 1. Intended outcome

Help non-native English speakers recall suitable workplace expressions more readily and use them comfortably in conversation. Learners should understand the communication purpose behind an expression and adapt it to their own situation, rather than reproduce a required script.

The experience teaches expressions through purpose and reasoning, then creates opportunities to use them in spoken conversation. Warmth, natural wording, and appropriate workplace tone matter alongside conveying meaning. Ordinary thinking pauses are acceptable.

## 2. Confirmed product decisions

| ID | Decision | Basis |
| --- | --- | --- |
| P01 | Scope the first release as a small, complete take-home submission. Prioritize a functioning end-to-end experience and explicitly defer extensions. | User accepted discussion question 1. |
| P02 | Target intermediate adults, approximately B1–B2, who can already converse in English but struggle to recall natural workplace wording. Use simple English explanations. | User accepted discussion question 2. This describes the target audience, not a proficiency test or certification claim. |
| P03 | A normal practice exchange contains 3–5 learner turns before coaching. | User refined the proposed 2–3 turns to 3–5. |
| P04 | The tutor begins with a scenario-appropriate opening question or prompt and follows up based on the learner's actual answers. | User described a starting question and answer-dependent follow-ups. |
| P05 | Voice leads the experience, including tutor responses and coaching; text supports understanding. | Explicit user direction preserved in the mockup handoff. |
| P06 | Assess the practice exchange across Fluency, Pronunciation, Naturalness, and Workplace tone. Give one integer score from 1–5 per supported dimension and no overall grade. Ground feedback in the learner's speech, identify one main improvement, and leave dimensions unscored when evidence is insufficient. | User accepted discussion question 5, refining the earlier request for multidimensional feedback. |
| P07 | Organize learning as scenario → communication purpose → expressions and reasoning → speaking practice. Include all seven existing purposes across hosting a meeting, casual talk, and one-on-one, using curated content and preset situations. No custom-scenario builder or personalization setup is required. | Established scenario direction; user accepted discussion question 10 for purpose coverage. |
| P08 | Deliver a web app with one portrait phone layout, using the mockup's 390:844 aspect ratio. Desktop browsers show the same portrait app centered in the available space. Provide immediate guest access without an account. | User refined question 9 during specification review: support only the phone ratio, including when running Docker on desktop. Recent sessions remains included. |
| P09 | End at a natural break once the communication goal has been demonstrated, after at least 3 learner turns and no later than turn 5. Acknowledge the final answer and explicitly switch to coaching without asking an unanswered roleplay question. | User accepted discussion question 4. |
| P10 | Offer a focused retry of 1–2 learner turns with a small variation, so the learner can apply the main coaching suggestion immediately. | User accepted discussion question 6. |
| P11 | Follow-ups may advance the realistic scene beyond the selected expression or purpose, while coaching continues to emphasize the selected skill. | User accepted discussion question 7. |
| P12 | Use hands-free conversation with automatic turn completion and spoken interruption. Provide explicit controls, including an “I'm done” fallback, and tolerate thinking pauses. | User accepted discussion question 8. |
| P13 | After retry, give targeted spoken feedback and a takeaway with an expression and its reasoning pattern. Keep the original exchange scores; do not automatically regrade four dimensions from the shorter retry. Offer another focused retry or finish. | User accepted discussion question 11. |
| P14 | Temporarily retain transcript, progress, and scores for 24 hours after the last practice activity, without application-saved learner recordings. Add Recent sessions for the same browser, without an account. | User selected temporary recovery in question 12 and requested Recent sessions; accepted questions 13–14. |
| P15 | Recent sessions includes unfinished and completed sessions. Resume continues unfinished practice; Review opens completed results; Practice again starts a new exchange. | User accepted discussion question 13. |
| P16 | Leaving practice saves it paused. Finish completes practice and retains the results. Explicit Delete or expiry clears the session. | User accepted discussion question 14. This replaces the earlier clear-on-exit proposal. |

The assignment's two-hour expectation guides scope; no new hard deadline was agreed in this discussion.

## 3. Learning journey

Choose a scenario → explore an expression and its purpose → complete a short spoken exchange → receive spoken coaching and multidimensional feedback → retry → leave with a takeaway.

### Explore

Expressions are connected to what the learner is trying to accomplish. Explain why the wording helps and when it fits. Learners should be able to hear the expression before using it.

The release includes seven purposes: meeting welcome, setting the agenda, meeting wrap-up, starting a casual conversation, following up, sharing progress, and asking for support. Use curated expressions and preset situations through one reusable practice flow.

### Practice

The tutor sets up the situation and opens the exchange in a role appropriate to that situation. The learner responds in their own words. Subsequent tutor turns use information from the learner's answers and maintain the workplace context.

The normal exchange lasts 3–5 learner turns. Tutor turns are not included in that count. Starting after the third learner turn, the tutor may finish at a natural break when the communication goal has been demonstrated. It must finish after the fifth learner turn even when the goal has not yet been met; coaching can explain what remains to work on.

On completion of roleplay, the tutor acknowledges the learner's final answer and makes a clear spoken and visible transition into coaching. It must not ask a new roleplay question and then switch to coaching before the learner can answer it. Ending roleplay does not force the learner to end the session: coaching and optional focused retries follow until the learner chooses Finish.

An illustrative progression for hosting a meeting is:

1. The tutor invites the learner to open the meeting.
2. After hearing the opening and topic, the tutor asks a relevant question about that topic or the intended decision.
3. After hearing the learner's answer, the tutor responds and follows up on a relevant detail.

This illustrates responsive conversation, not a fixed dialogue. Follow-ups may advance the scene beyond the selected purpose: welcoming colleagues can lead into the meeting's goal or an attendee's question. The selected skill remains the coaching focus, but the tutor need not invent a problem with that skill if the learner has already demonstrated it. The learner need not use the suggested expression verbatim.

### Coaching, retry, and takeaway

Spoken coaching follows the short exchange. Feedback should be grounded in what the learner actually said, with supporting text available. The tutor's coaching role must be distinguishable from its roleplay character.

Assess the full practice exchange in four dimensions, each on an integer 1–5 scale:

| Dimension | Meaning |
| --- | --- |
| Fluency | The flow and phrasing of spoken contributions, allowing normal thinking pauses. |
| Pronunciation | How understandable the learner's speech is, including sounds, stress, and phrasing. Having a particular native accent is not the goal. |
| Naturalness | Whether the wording is idiomatic and suitable for the intended meaning. |
| Workplace tone | Whether warmth, directness, and formality suit the situation and relationships. |

There is no overall grade. Coaching uses examples from the learner's actual contributions and selects one main improvement to practice. A dimension without sufficient evidence remains unscored with an explanation. Audio-dependent dimensions cannot be inferred solely from a transcript. Section 8 defines rubric anchors and evidence requirements.

The focused retry lasts 1–2 learner turns and uses a small variation of the same situation. Its purpose is to apply the coaching suggestion, rather than repeat the entire exchange. Afterward, give brief spoken feedback on the targeted change and offer another retry or a takeaway. Keep the original exchange scores available; the shorter retry does not automatically receive a fresh four-score assessment.

The mockup's prepared scores and scripted improvements establish no real assessment behavior. Retry feedback must reflect what happened, with no guaranteed score increase.

## 4. Core requirements

- The learner can speak to the tutor and receive audible, context-appropriate responses.
- A normal practice exchange supports 3–5 learner turns before switching to coaching.
- Tutor follow-ups respond to details in the learner's answers rather than merely advancing a fixed question list.
- Practice allows suitable alternative wording; copying the displayed expression is not a success condition.
- The tutor delivers coaching aloud and provides secondary written support.
- Assessment summarizes the full exchange in four separate 1–5 dimensions, with no aggregate grade and no invented score for unsupported dimensions.
- A focused retry gives the learner 1–2 turns to apply the main suggestion in a slightly varied situation.
- Explanations suit intermediate learners and use simple English.
- All seven purposes share one reusable practice experience, with curated expressions and preset situations.
- Recent sessions preserves unfinished work and completed results in the same browser for 24 hours after practice activity, with explicit deletion.
- The release demonstrates a working learning journey within a deliberately small take-home scope.

Section 11 gives concrete acceptance scenarios.

## 5. Navigation and Recent sessions

### Portrait presentation

- Use one portrait app surface for every screen, including Conversations, Recent sessions, practice, feedback, and sheets. Its reference and maximum size is **390 × 844 CSS pixels**, with a **390:844 width-to-height ratio**. Reduce its bounds only when the available viewport is smaller.
- On desktop, center that surface against a simple surrounding background. Extra browser width does not expand the app or introduce desktop columns, side panels, or a separate navigation layout.
- Fit the portrait surface within smaller available viewports while retaining its aspect ratio. Keep text readable and controls at least 44×44 CSS pixels; reflow and scroll content inside the surface instead of uniformly shrinking the whole interface. A phone viewport with a different ratio may have space around the app.
- Support one portrait layout. A landscape or tablet-specific interface is outside release scope; a wide desktop browser still hosts the same portrait surface.

### Navigation

Provide two primary destinations: **Conversations** and **Recent sessions**. Conversation selection leads to expression exploration and practice. Recent sessions is an intentional addition to the original six-screen mockup.

Each recent entry shows scenario, purpose, last practice time, and whether it is unfinished or completed. Make the 24-hour retention window clear. An empty page explains that starting practice creates an entry.

- **Resume** restores an unfinished session at its saved phase: roleplay, coaching, or focused retry. It does not restart the original exchange or reset the turn count. Resume is an explicit user action; microphone access is relevant only when the restored phase requires speaking.
- **Review** opens a completed session's transcript, original scores, coaching, retry feedback if present, and takeaway. It does not activate the microphone or reopen that session for new answers.
- **Practice again** creates a new session for the same purpose, with a fresh exchange and assessment. It does not overwrite completed results.
- **Delete** removes the selected session. If it is active, stop its capture and audio first.
- Only one voice session can be active at a time in the browser. Starting or resuming another session pauses and saves the previous unfinished one.
- A guest can access only sessions associated with that browser. Recent sessions must not expose another guest's transcript or results.

Recent sessions is temporary browser-associated history. It does not provide cross-device access, an account, or indefinite progress tracking. Clearing browser identification can make server-side guest sessions inaccessible until they expire; do not promise recovery without that browser association.

## 6. Delivery constraints carried into technical design

The assignment requires a frontend and backend for a real-time LiveKit voice tutor, Redis-backed conversation state, and startup through Docker Compose using a root `.env` with a complete `.env.example`.

Docker Compose on a desktop serves the same portrait browser interface. The service packaging does not require a desktop-sized application layout.

Required submission materials include the exact assignment in `PROMPT.md`, architecture and tradeoffs in `README.md`, an accurate `workflow.md`, a demonstration video, and a zip of the repository including `.git`. The README must discuss how the design would change for 10,000 concurrent sessions.

Providers, framework, backend language, state schema, and deployment architecture have not been selected. Technical design follows the product behavior and acceptance criteria established here.

## 7. Interaction contract

These controls define the learner-visible behavior independently of the eventual implementation stack.

### Turn-taking and tutor behavior

- Ask one question at a time. Normal roleplay turns should usually be one or two short sentences, leaving most of the speaking opportunity to the learner.
- A learner turn is one submitted response to the current tutor prompt. Silence, background noise, help requests, and control actions do not advance the 3–5-turn count. A genuine brief answer can count even when it supplies insufficient evidence for scoring.
- Automatically detect completion using speech context and pauses. An ordinary thinking pause must not automatically become a completed response. A visible **I'm done** control submits the current response if the tutor keeps waiting; it does nothing to the turn count when there is no speech to submit.
- If the learner's meaning is unclear, ask a short clarification within the remaining exchange turn budget instead of inventing it. After turn 5, explain any uncertainty in coaching rather than extending roleplay. Do not manufacture details for assessment from an unreliable transcript.
- Speaking while the tutor speaks interrupts its audio. The tutor must respond to the new learner contribution without later resuming an obsolete reply.
- If the tutor starts prematurely and the learner continues the same answer, accept that continuation without counting it as two answers. During coaching, spoken questions about feedback stay in the coaching phase and do not add roleplay or retry turns.
- Conversation follows the scenario and the learner's actual answers. Teaching material supplies useful language and objectives, not a script the learner must reproduce.
- Do not interrupt a roleplay answer with corrections. At the end of the exchange, acknowledge the final response and use a signpost such as “Let's look at what worked and one thing to try.” Change the visible role from conversation partner to coach.

### Controls

| Control | User-visible contract |
| --- | --- |
| Start practice | Explain the microphone requirement, request access on user action, connect, then speak the setup and first prompt. No microphone use before starting. |
| I'm done | Submit the current spoken response without waiting for automatic completion. It is a button, not a requirement to speak a command. |
| Pause | Stop capture and tutor playback. Preserve completed responses and progress. An unfinished answer is not submitted; tell the learner that it needs to be tried again. No pending reply may start playing while paused. |
| Resume | Explicitly resume the same session and phase. In roleplay or retry, return to the same prompt after an unfinished answer, or continue once from a submitted answer that was awaiting a reply. Resuming coaching restores coaching without restarting roleplay. |
| Mute | Turn off microphone capture while allowing tutor audio to continue. Muting does not submit an answer or count as a turn. If it interrupts an unfinished answer, apply the same visible retry behavior as Pause. |
| Hint | Pause roleplay and capture, provide a short spoken starter linked to the current purpose, and show its words. Help does not count as a learner turn. Returning to practice explicitly resumes the pending prompt. |
| Hear Alex | Replay the last tutor message without creating another conversation turn. Suspend capture during replay; restore listening only if it was active before replay. A paused exchange remains paused. |
| Show words / Transcript | Reveal optional text. Text starts collapsed during practice; the learner's visibility choice persists for the current practice session. |
| Finish | Stop capture and roleplay playback, complete the session, and present available feedback and a takeaway using only submitted responses. The learner may finish before turn 3. Do not fabricate scores or claim practice occurred when no answer was completed. A completed session can be reviewed; further practice starts a new session. |
| Back to conversations | Stop all capture/playback and return to selection. Save unfinished work as paused, including its current phase. Completed sessions remain completed. This action does not delete data. |

Ready, connecting, tutor speaking, listening, thinking, paused, coaching, and connection problems must have explicit text labels. Animation and color are supplemental. Voice controls must remain available during slow processing.

## 8. Assessment contract

Scores are formative feedback for this exchange. They do not certify a proficiency level or represent progress over time. They are not averages of hidden per-turn grades.

### Rubric anchors

| Score | Fluency | Pronunciation | Naturalness | Workplace tone |
| --- | --- | --- | --- | --- |
| 1 | Repeated breakdowns make the intended message difficult to follow. | Frequent unintelligibility prevents understanding much of the message. | Wording frequently obscures the intended meaning. | Wording repeatedly works against the communication purpose or relationship. |
| 2 | Frequent restarts or disrupted phrasing require substantial listener effort. | Repeated sound or stress problems require substantial listener effort. | The message is recoverable, but recurring awkward constructions impede it. | Several choices are too abrupt, vague, or mismatched in formality. |
| 3 | The message is generally easy to follow despite some disrupted phrasing. | The message is generally understandable, with some unclear words or stress. | Most wording is usable; several expressions could be more idiomatic. | Tone is broadly appropriate, with a clear opportunity to adjust warmth or directness. |
| 4 | Contributions flow comfortably; occasional repairs do not disrupt understanding. | Speech is consistently clear; minor issues do not impede understanding. | Wording is consistently natural, with only minor awkwardness. | Warmth, directness, and formality consistently suit the situation. |
| 5 | Phrasing and pacing flexibly support the message throughout the sample. | Sounds, stress, and phrasing make the message readily understandable throughout. | Expressions are idiomatic and flexibly adapted to the learner's meaning. | Language is well judged and adapts to the other participant's responses. |

Normal thinking pauses are not a defect in themselves. Pronunciation evaluates intelligibility, not conformity to a native accent. Tone depends on the specified roles and situation; warmth is not always more important than directness. A high score never requires the exact displayed phrase.

### Evidence and feedback

- Assess completed learner responses from the practice exchange. Exclude tutor audio, hints, unsubmitted fragments, and the later retry.
- Fluency and Pronunciation require usable learner audio. Naturalness and Workplace tone require sufficiently reliable wording and context. A transcript alone cannot support all four dimensions.
- Do not issue a full scorecard from silence, unintelligible input, or only isolated acknowledgments such as “yes” and “okay.” Each dimension can independently be unavailable.
- Explain unavailable results accurately: **Not enough speech**, **Audio unclear**, or **Assessment unavailable**, as applicable. A service failure is not a low score.
- For each score, provide a short explanation and evidence linked to an actual learner turn. Naturalness/tone feedback can quote wording; audio feedback should describe an observed feature without inventing a quote or pronunciation error.
- Spoken coaching identifies a useful strength, gives one prioritized improvement, and models a suitable alternative with a short explanation of why it helps. Do not read all four numbers aloud by default.
- If the selected skill was already demonstrated, acknowledge it and offer a relevant refinement or transfer challenge. Do not manufacture an error to justify a retry.
- The normal path must support genuine assessment of all four dimensions when there is adequate speech. Permanent “unavailable” placeholders for audio dimensions do not satisfy the release requirement.

The technical specification must define how evidence sufficiency is detected, how audio reaches the evaluator, and how the rubric is checked against representative speech. Those choices must satisfy these product contracts rather than replace audio evidence with transcript guesses. A deterministic rule for sample eligibility belongs in that specification; no universal minimum number of seconds or words is claimed here.

## 9. Content and completion details

### Content shape

Each purpose has a main expression, one alternative, a plain-English explanation of why it works and when it fits, and a short example. It also supplies a preset situation, learner/tutor roles, a communication goal, and a hint starter. **Listen** provides audible expression playback; **Practice** opens the corresponding scene.

Launch coverage includes all seven existing purposes. There is no progression lock: learners can choose any available purpose. They may introduce their own details while speaking; a separate personalization form or custom-scenario builder is outside release scope.

| Scenario | Purpose | Preset situation |
| --- | --- | --- |
| Hosting a meeting | Welcome everyone | Open a weekly team meeting with colleagues. |
| Hosting a meeting | Set the agenda | Explain the goal and intended outcome of a project discussion. |
| Hosting a meeting | Wrap up | Close a team discussion and confirm decisions or next steps. |
| Casual talk | Start a conversation | Begin a friendly conversation with a colleague before work starts. |
| Casual talk | Follow up | Ask a colleague about a presentation they mentioned earlier. |
| One-on-one | Share progress | Give a manager or colleague a concise project update. |
| One-on-one | Ask for support | Explain a blocker and make a specific request for help. |

### Retry and takeaway

The completion behavior is:

1. Invite the learner to apply the main suggestion in a slightly varied prompt.
2. Finish after one response if it demonstrates the target, or use one relevant follow-up and finish after the second response.
3. Give brief spoken feedback on the targeted change. Acknowledge improvement only when the new response supports it; otherwise offer one concrete adjustment without requiring a passing grade.
4. Keep the original exchange's four scores labeled as that exchange's assessment. Do not automatically replace them with scores for the shorter retry or show invented improvement deltas.
5. Offer another focused retry or Finish. Finish completes the session and opens its takeaway. The learner can also skip retry and finish immediately after the original coaching.

The takeaway identifies the practiced purpose, one expression to reuse, and the communication pattern or reasoning behind it. It can be heard aloud and read, and remains available with completed results until session expiry or deletion. It is not an independent saved-expression library. **Back to conversations** returns to scenario selection and preserves the completed session in Recent sessions.

## 10. Recovery and data lifecycle

### Session lifecycle

| State | Meaning and transitions |
| --- | --- |
| In progress | The learner is in roleplay, coaching, or an optional retry. Completing the 3–5-turn roleplay moves to coaching within the same session. |
| Paused | An unfinished session was paused, left, refreshed, or disconnected. Save its phase and completed work. Resume continues that phase. |
| Completed | The learner chose Finish. Preserve available results and the takeaway for Review. Practice again creates a new session rather than reopening the completed one. |
| Deleted or expired | Session content is unavailable and cannot be resumed or reviewed. Offer a fresh start. |

### Retention and recovery

- Temporarily store each guest session's selected purpose, preset situation, phase, progress, completed transcript, original assessment, coaching, retry feedback, and takeaway as available. Associate access with the same browser; no account is required.
- Retain each session for at most 24 hours after its last practice activity. Starting/resuming practice, submitting answers, requesting active help, or finishing can renew this interval. Passive heartbeats, listing Recent sessions, and reviewing completed results do not renew it.
- **Back to conversations** saves; **Finish** completes; **Delete** removes. Deletion applies to application session data and does not promise deletion from external providers' systems.
- The app does not persist learner recordings. Audio may be held temporarily for live processing and assessment, then discarded. Avoid copying transcripts or learner audio into application logs. Provider processing and retention must be documented separately in technical design.
- Refresh or reconnect restores completed work and the saved phase, but returns an unfinished session to a paused state. No microphone capture resumes without an explicit user action. A completed session remains a read-only review.
- If Pause, Mute, Hint, replay, navigation, or connection loss cuts off capture before an answer is submitted, that fragment is not counted or scored. Explain that the learner needs to answer the current prompt again. Preserve earlier completed responses. This does not apply to the learner interrupting tutor playback: accept and process that learner contribution normally.
- If audio evidence is lost during recovery, do not reconstruct audio scores from text. Preserve scores already obtained; explain any unavailable pending assessment and offer another speaking attempt.
- Persist completed results as they become available. Pending work must not update a deleted or expired session or start playback after the learner has left it.
- Remove expired entries from Recent sessions. A stale link to one explains that it expired and offers a fresh start; it must not appear to have recovered deleted history.

| Failure | Required experience |
| --- | --- |
| Microphone denied or unavailable | Explain how to retry permission/access and allow return to expressions. Do not present a simulated listening state. |
| Connection lost | Stop capture/playback, mark the exchange paused, and offer reconnect or exit. Restore completed work according to the lifecycle above. |
| Slow tutor response | Keep a truthful processing status and working Pause/Finish controls. Do not repeat questions or duplicate learner turns. |
| Response generation fails | Offer retry of the pending response from the last completed turn or exit. Never insert a fabricated response into the transcript. |
| Speech playback fails | Show the available words, explain the audio failure, and offer replay. Do not imply that coaching was heard successfully. |
| Assessment fails | Keep the completed exchange and available feedback. Mark affected scores unavailable and offer assessment retry if the required evidence is still available. |

Late replies or repeated connection events must not play obsolete speech, advance the turn count twice, or overwrite the current feedback screen. The technical specification will define cancellation and state ownership to provide this behavior.

## 11. Acceptance scenarios

These are the observable checks the implementation and technical plan should support.

| ID | Scenario | Acceptance condition |
| --- | --- | --- |
| A01 | Guest opens the app on phone or desktop | Scenario selection is immediately usable without sign-up. Both hosts display the same 390:844 portrait app surface with readable text and reachable controls; a wide browser centers it instead of producing a desktop layout. |
| A02 | Learner selects any of the seven purposes | Its expression, alternative, explanation, audible playback, and matching practice entry are available. |
| A03 | Normal conversation | The tutor gives an audible setup and opening, then produces follow-ups grounded in the actual learner answers. Prepared sample playback cannot substitute for this check. |
| A04 | Goal achieved after 3 or 4 turns | The tutor can finish at a natural break, acknowledge the last answer, and switch explicitly to coaching without leaving a new question unanswered. |
| A05 | Goal not yet demonstrated after turn 5 | The tutor ends roleplay after the fifth learner turn and gives constructive coaching instead of adding a sixth question. |
| A06 | Learner pauses mid-answer | An ordinary thinking pause does not trigger an intrusive substantive reply. If completion is not detected when the learner is done, **I'm done** submits exactly once. The technical test plan must define representative audio samples. |
| A07 | Learner interrupts tutor speech | Playback stops and the exchange responds to the learner's new contribution; an obsolete response never resumes later. |
| A08 | Learner uses Pause, Mute, Hint, or replay | Capture/playback and turn counting follow the control table. No helper audio or incomplete answer is mistaken for an assessed learner turn. |
| A09 | Adequate clear speech | Four separate 1–5 scores have actual supporting evidence and explanations. Spoken coaching selects one useful improvement; no aggregate grade appears. |
| A10 | Insufficient or unclear speech | Affected dimensions remain unscored with the right explanation. Silence and isolated acknowledgments never produce a fabricated full scorecard. |
| A11 | Focused retry | A slight variation elicits 1–2 learner turns. Feedback accurately addresses the targeted suggestion. The original exchange's scores stay labeled and unchanged; another retry or Finish is available. |
| A12 | Learner finishes early | Capture/playback stop. Feedback uses only completed work; no-completed-answer sessions do not claim achievement or invent scores. |
| A13 | Page refresh or lost connection | Recovery restores the saved phase and completed work, does not double-count turns, and requires an explicit action before microphone capture resumes. A partial answer is retried. |
| A14 | Provider or playback failure | The app follows the failure table, keeps controls usable, and never substitutes prepared successful responses or scores. |
| A15 | Session expiry or Delete | Session content is removed and cannot be resumed/reviewed. Back to conversations does not trigger deletion. Listing or reviewing completed sessions does not extend their retention. |
| A16 | Reviewer's clean checkout | Supplying the documented root `.env` and running Docker Compose starts the real frontend, backend, and Redis-backed voice experience. Required submission documents and video are present. |
| A17 | Learner leaves and resumes practice | Recent sessions shows the unfinished session. Resume restores its purpose, phase, and accepted turn count instead of restarting it. |
| A18 | Learner reviews completed practice | Review shows the completed transcript, original scores, feedback, and takeaway without microphone capture. Practice again creates a distinct session without altering those results. |
| A19 | Learner switches sessions | The previous unfinished voice session is paused and saved. Only the newly resumed session can capture or play live conversation audio. |

Visual acceptance uses the 390×844 app reference. In a shorter 375×667 browser viewport and desktop browser viewports, the app retains the same 390:844 aspect ratio, fits within the available area, and keeps content scrollable inside it. There is no alternate 375×667 app ratio or wide desktop layout. Verify readable text, touch targets of at least 44×44 CSS pixels, visible keyboard focus, transcript access, and reachable voice controls. Browser support, secure microphone access for physical phones, latency targets, and failure timeouts must be made concrete in technical design and the verification plan.

## 12. Deferred scope and next artifact

The release excludes native apps, separate desktop/tablet/landscape layouts, accounts, cross-device or long-term history, saved-expression libraries, streaks, leaderboards, aggregate grades, placement tests, bilingual instruction, an open-ended conversation mode, curriculum generation, and a custom-scenario builder. Temporary Recent sessions is included explicitly.

The provisional Good Company identity and Alex tutor name can carry over from the mockup for this release. They are reversible presentation defaults, not brand-development work. Preserve the mockup's voice emphasis, restrained palette, typography, and optional text without treating its simulated controls as implementation logic.

Once this product specification is reviewed, a separate technical specification should select the implementation and provider stack, define session state and audio assessment, establish measurable turn-taking and latency checks, and map these acceptance scenarios to verification. Product implementation has not started.
