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
| P03 | A normal practice exchange contains 2–3 learner turns before coaching. Coaching can address problems found across those turns. | User's latest written-spec review restores 2–3 turns and explicitly requests advice on problems within the exchange. |
| P04 | Practice follows spoken Q&A: the tutor asks a scenario-appropriate question or prompt, the learner answers in their own words, and the tutor responds with an answer-dependent follow-up. Each completed learner answer counts as one learner turn; the tutor's question does not add a turn. | User described a starting question and answer-dependent follow-ups, then asked to clarify the Q&A format during visual review. |
| P05 | Voice leads the experience, including tutor responses and coaching; text supports understanding. Tutor speech should sound natural and fluent, with appropriate tone, intonation, emphasis, and pacing. | Original voice-first direction plus the user's latest request for a native speaking experience with tone and fluency. |
| P06 | Use LLM judgment to assess the practice exchange across Fluency, Pronunciation, Naturalness, and Workplace tone. Give one integer score from 1–5 per supported dimension and no overall grade. Ground feedback in the learner's speech, provide actionable advice on observed problems across the exchange, select one retry priority, and leave dimensions unscored when evidence is insufficient. | User accepted discussion question 5 and clarified in written review that LLM analysis and scoring should be flexible. |
| P07 | Organize learning as scenario → communication purpose → expressions and reasoning → speaking practice. Present scenarios in this order: Hosting a meeting → One-on-one → Casual talk. Include three purposes in each: nine total, using curated content and preset situations. No custom-scenario builder or personalization setup is required. | User expanded coverage to three purposes per scenario during visual review, accepted Close a conversation and Ask for feedback, and requested Casual talk after Meeting and One-on-one. |
| P08 | Deliver a web app with one portrait phone layout, using the mockup's 390:844 aspect ratio. Desktop browsers show the same portrait app centered in the available space. Provide immediate guest access without an account. | User refined question 9 during specification review: support only the phone ratio, including when running Docker on desktop. Recent sessions remains included. |
| P09 | End at a natural break once the communication goal has been demonstrated, after at least 2 learner turns and no later than turn 3. Acknowledge the final answer and explicitly switch to coaching on the completed exchange without asking an unanswered roleplay question. | User accepted adaptive completion in question 4, then changed its bounds to match P03 during written-spec review. |
| P10 | Offer a focused retry of 1–2 learner turns with a small variation, so the learner can apply the main coaching suggestion immediately. | User accepted discussion question 6. |
| P11 | Follow-ups may advance the realistic scene beyond the selected expression or purpose, while coaching continues to emphasize the selected skill. | User accepted discussion question 7. |
| P12 | Use hands-free conversation with automatic turn completion and spoken interruption. Provide explicit controls, including an “I'm done” fallback, and tolerate thinking pauses. | User accepted discussion question 8. |
| P13 | After retry, give targeted spoken feedback and a takeaway with an expression and its reasoning pattern. Keep the original exchange scores; do not automatically regrade four dimensions from the focused retry. Offer another focused retry or finish. | User accepted discussion question 11. |
| P14 | Temporarily retain transcript, progress, and scores for 24 hours after the last practice activity, without application-saved learner recordings. Add Recent sessions for the same browser, without an account. | User selected temporary recovery in question 12 and requested Recent sessions; accepted questions 13–14. |
| P15 | Recent sessions includes unfinished and completed sessions. Resume continues unfinished practice; Review opens completed results; Practice again starts a new session for the same purpose with a fresh exchange and assessment. | User accepted discussion question 13. Section 5 clarifies the new-session behavior in response to the user's question about repeated questions. |
| P16 | Leaving practice saves it paused. Finish completes practice and retains the results. Explicit Delete or expiry clears the session. | User accepted discussion question 14. This replaces the earlier clear-on-exit proposal. |
| P17 | Build the real voice experience with the LiveKit SDK and LLM-driven conversation and speaking-quality assessment. Select models that can support the required speech delivery and audio-grounded feedback. | User explicitly confirmed LiveKit SDK and an LLM behind the experience during written-spec review. Specific providers remain for technical design. |

The assignment's two-hour expectation guides scope; no new hard deadline was agreed in this discussion.

## 3. Learning journey

Choose a scenario → explore an expression and its purpose → complete a short spoken exchange → receive spoken coaching and multidimensional feedback → retry → leave with a takeaway.

### Explore

Expressions are connected to what the learner is trying to accomplish. Explain why the wording helps and when it fits. Learners should be able to hear the expression before using it.

The release includes nine purposes, three per scenario, displayed in this order: meeting welcome, setting the agenda, meeting wrap-up; sharing progress, asking for support, asking for feedback; starting a casual conversation, following up, closing a conversation. Use curated expressions and preset situations through one reusable practice flow.

### Practice

The tutor sets up the situation and opens the exchange in a role appropriate to that situation. Practice takes the form of spoken Q&A: tutor question or prompt → learner answer → tutor acknowledgment and relevant follow-up → learner answer. Each learner answer is one learner turn. The learner responds in their own words, and the tutor uses information from those answers to maintain the workplace context. Questions can be natural invitations such as “Shall we get started?”; answers may include several sentences or a question back to the tutor.

The normal exchange lasts 2–3 learner turns. Tutor turns are not included in that count. After the second learner turn, the tutor may finish at a natural break when the communication goal has been demonstrated. Otherwise, it asks one relevant follow-up and finishes after the third learner turn even when the goal has not yet been met; coaching explains what remains to work on. A learner may explicitly finish earlier.

On completion of roleplay, the tutor acknowledges the learner's final answer and makes a clear spoken and visible transition into coaching. It must not ask a new roleplay question and then switch to coaching before the learner can answer it. Ending roleplay does not force the learner to end the session: coaching and optional focused retries follow until the learner chooses Finish.

An illustrative progression for hosting a meeting is:

1. **Tutor:** “Everyone's here. Shall we get started?” **Learner answer 1:** “Good to see everyone. Thanks for making time. Let's review the project timeline.”
2. **Tutor:** “Sounds good. What should we decide about the timeline today?” **Learner answer 2:** “I'd like us to agree on a launch date.”
3. The tutor acknowledges the second answer and moves to coaching if the goal is demonstrated; otherwise, it asks one final relevant follow-up and coaches after learner answer 3.

This illustrates responsive conversation, not a fixed dialogue. Follow-ups may advance the scene beyond the selected purpose: welcoming colleagues can lead into the meeting's goal or an attendee's question. The selected skill remains the coaching focus, but the tutor need not invent a problem with that skill if the learner has already demonstrated it. The learner need not use the suggested expression verbatim.

### Coaching, retry, and takeaway

Spoken coaching follows the short exchange. Feedback considers all completed learner turns and can address problems in any of them, including an earlier answer. Give concrete advice and an example for each meaningful issue raised. Keep the spoken summary concise, with turn-specific detail available in coaching notes and through spoken follow-up questions. The tutor's coaching role must be distinguishable from its roleplay character.

Assess the full practice exchange in four dimensions, each on an integer 1–5 scale:

| Dimension | Meaning |
| --- | --- |
| Fluency | The flow and phrasing of spoken contributions, allowing normal thinking pauses. |
| Pronunciation | How understandable the learner's speech is, including sounds, stress, intonation, and phrasing. Having a particular native accent is not the goal. |
| Naturalness | Whether the wording is idiomatic and suitable for the intended meaning. |
| Workplace tone | Whether wording and spoken delivery convey warmth, directness, and formality suited to the situation and relationships. |

There is no overall grade. The LLM judges the exchange in context using the rubric as guidance. Coaching uses examples from the learner's actual contributions and selects one main improvement for the focused retry; that priority does not limit the other useful advice available for the exchange. A dimension without sufficient evidence remains unscored with an explanation. Audio-dependent judgments cannot be inferred solely from a transcript. Section 8 defines rubric anchors and evidence requirements.

The focused retry lasts 1–2 learner turns and uses a small variation of the same situation. Its purpose is to apply the coaching suggestion, rather than repeat the entire exchange. Afterward, give brief spoken feedback on the targeted change and offer another retry or a takeaway. Keep the original exchange scores available; the focused retry does not automatically receive a fresh four-score assessment.

The mockup's prepared scores and scripted improvements establish no real assessment behavior. Retry feedback must reflect what happened, with no guaranteed score increase.

## 4. Core requirements

- The learner can speak to an LLM-driven tutor through LiveKit and receive natural, fluent, context-appropriate spoken responses with expressive tone and intonation.
- A normal practice exchange supports 2–3 learner answers in spoken Q&A before switching to coaching; tutor questions do not count toward that limit.
- Tutor follow-ups respond to details in the learner's answers rather than merely advancing a fixed question list.
- Practice allows suitable alternative wording; copying the displayed expression is not a success condition.
- The tutor delivers coaching aloud, can advise on problems across all completed exchange turns, and provides secondary written support.
- LLM assessment summarizes the full exchange in four separate 1–5 dimensions, using contextual judgment and actual speech evidence, with no aggregate grade and no invented score for unsupported dimensions.
- A focused retry gives the learner 1–2 turns to apply the main suggestion in a slightly varied situation.
- Explanations suit intermediate learners and use simple English.
- All nine purposes, three per scenario, share one reusable practice experience, with curated expressions and preset situations.
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

Conversations displays **Hosting a meeting → One-on-one → Casual talk**, with three purposes under each scenario. This is a presentation order, not a progression lock.

Each recent entry shows scenario, purpose, last practice time, and whether it is unfinished or completed. Make the 24-hour retention window clear. An empty page explains that starting practice creates an entry.

- **Resume** restores an unfinished session at its saved phase: roleplay, coaching, or focused retry. It does not restart the original exchange or reset the turn count. Resume is an explicit user action; microphone access is relevant only when the restored phase requires speaking.
- **Review** opens a completed session's transcript, original scores, coaching, retry feedback if present, and takeaway. It does not activate the microphone or reopen that session for new answers.
- **Practice again** creates a new session for the same purpose, with a full 2–3-turn exchange and a fresh assessment based on the new answers. Follow-ups respond to those answers; the app does not replay the completed session's question sequence. Completed results remain unchanged.
- **Delete** removes the selected session. If it is active, stop its capture and audio first.
- Only one voice session can be active at a time in the browser. Starting or resuming another session pauses and saves the previous unfinished one.
- A guest can access only sessions associated with that browser. Recent sessions must not expose another guest's transcript or results.

The draft behavior for **Practice again** is to vary the opening prompt or one small detail of the preset situation from the completed session, while preserving the selected purpose, learner/tutor roles, and intended difficulty. For example, practicing a meeting welcome again might change a timeline discussion to a weekly planning meeting. Familiar question types may recur; every question need not be globally unique. The learning objective and reusable expressions remain consistent.

Practice again differs from a **focused retry**: Practice again starts a full new exchange with its own scores; a focused retry stays in the current session for 1–2 learner turns to apply one coaching suggestion and preserves the original scores.

Recent sessions is temporary browser-associated history. It does not provide cross-device access, an account, or indefinite progress tracking. Clearing browser identification can make server-side guest sessions inaccessible until they expire; do not promise recovery without that browser association.

## 6. Delivery constraints carried into technical design

The assignment requires a frontend and backend for a real-time LiveKit voice tutor, Redis-backed conversation state, and startup through Docker Compose using a root `.env` with a complete `.env.example`. The user has confirmed the LiveKit SDK and LLM-driven conversation and assessment as the implementation direction.

The voice model and assessment design must preserve access to learner audio for judgments about delivery. LiveKit supports both direct speech-to-speech models and a speech-to-text → LLM → text-to-speech pipeline. Its [pipeline comparison](https://docs.livekit.io/agents/models/pipelines.md), checked on 2026-09-26, explains that direct audio input preserves vocal cues lost in transcription. A speech-to-speech model is a strong candidate for the requested natural experience; technical design must evaluate it against voice quality, turn control, transcript recovery, and assessment needs before selecting providers. Audio understanding alone does not establish scoring quality: assessment still needs representative speech checks.

Docker Compose on a desktop serves the same portrait browser interface. The service packaging does not require a desktop-sized application layout.

Required submission materials include the exact assignment in `PROMPT.md`, architecture and tradeoffs in `README.md`, an accurate `workflow.md`, a demonstration video, and a zip of the repository including `.git`. The README must discuss how the design would change for 10,000 concurrent sessions.

Providers, framework, backend language, state schema, and deployment architecture have not been selected. Technical design follows the product behavior and acceptance criteria established here.

## 7. Interaction contract

These controls define the learner-visible behavior independently of the eventual implementation stack.

### Turn-taking and tutor behavior

- Speak with natural phrasing, connected rhythm, meaningful emphasis, and intonation appropriate to the situation. Keep a clear, comfortable pace for intermediate learners. Roleplay should sound like a workplace conversation; coaching should sound like a supportive explanation. Modeled expressions should demonstrate the delivery being taught.
- Ask one question at a time. Normal roleplay turns should usually be one or two short sentences, leaving most of the speaking opportunity to the learner.
- A learner turn is one submitted learner answer to the current tutor question or prompt. The tutor's question and acknowledgment do not advance the 2–3-turn count. Silence, background noise, help requests, and control actions do not advance it either. A genuine brief answer can count even when it supplies insufficient evidence for scoring.
- Automatically detect completion using speech context and pauses. An ordinary thinking pause must not automatically become a completed response. A visible **I'm done** control submits the current response if the tutor keeps waiting; it does nothing to the turn count when there is no speech to submit.
- If the learner's meaning is unclear, ask a short clarification within the remaining exchange turn budget instead of inventing it. After turn 3, explain any uncertainty in coaching rather than extending roleplay. Do not manufacture details for assessment from an unreliable transcript.
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
| Finish | Stop capture and roleplay playback, complete the session, and present available feedback and a takeaway using only submitted responses. The learner may finish before turn 2. Do not fabricate scores or claim practice occurred when no answer was completed. A completed session can be reviewed; further practice starts a new session. |
| Back to conversations | Stop all capture/playback and return to selection. Save unfinished work as paused, including its current phase. Completed sessions remain completed. This action does not delete data. |

Ready, connecting, tutor speaking, listening, thinking, paused, coaching, and connection problems must have explicit text labels. Animation and color are supplemental. Voice controls must remain available during slow processing.

## 8. Assessment contract

Scores are formative feedback for this exchange. They do not certify a proficiency level or represent progress over time. They are not averages of hidden per-turn grades.

The LLM evaluates meaning and speaking quality holistically. The anchors guide consistent interpretation; they are not a phrase-matching checklist or a formula based on word counts, pause counts, or error totals. The evaluator can weigh the communication purpose, relationships, wording, and audible delivery together. Application validation checks that returned scores, evidence references, and availability states are structurally valid; it does not replace contextual judgment with hard-coded language rules.

### Rubric anchors

| Score | Fluency | Pronunciation | Naturalness | Workplace tone |
| --- | --- | --- | --- | --- |
| 1 | Repeated breakdowns make the intended message difficult to follow. | Frequent unintelligibility prevents understanding much of the message. | Wording frequently obscures the intended meaning. | Wording repeatedly works against the communication purpose or relationship. |
| 2 | Frequent restarts or disrupted phrasing require substantial listener effort. | Repeated sound or stress problems require substantial listener effort. | The message is recoverable, but recurring awkward constructions impede it. | Several choices are too abrupt, vague, or mismatched in formality. |
| 3 | The message is generally easy to follow despite some disrupted phrasing. | The message is generally understandable, with some unclear words or stress. | Most wording is usable; several expressions could be more idiomatic. | Tone is broadly appropriate, with a clear opportunity to adjust warmth or directness. |
| 4 | Contributions flow comfortably; occasional repairs do not disrupt understanding. | Speech is consistently clear; minor issues do not impede understanding. | Wording is consistently natural, with only minor awkwardness. | Warmth, directness, and formality consistently suit the situation. |
| 5 | Phrasing and pacing flexibly support the message throughout the sample. | Sounds, stress, intonation, and phrasing make the message readily understandable throughout. | Expressions are idiomatic and flexibly adapted to the learner's meaning. | Wording and delivery are well judged and adapt to the other participant's responses. |

Normal thinking pauses are not a defect in themselves. Pronunciation evaluates intelligibility, not conformity to a native accent. Tone depends on the specified roles and situation; warmth is not always more important than directness. A high score never requires the exact displayed phrase.

### Evidence and feedback

- Assess completed learner responses from the practice exchange. Exclude tutor audio, hints, unsubmitted fragments, and the later retry.
- Fluency and Pronunciation require usable learner audio. Naturalness and Workplace tone require sufficiently reliable wording and context; comments on vocal tone, emphasis, or intonation also require audio. If only wording supports a tone score, explain that limited basis. A transcript alone cannot support all four dimensions.
- Do not issue a full scorecard from silence, unintelligible input, or only isolated acknowledgments such as “yes” and “okay.” Each dimension can independently be unavailable.
- Explain unavailable results accurately: **Not enough speech**, **Audio unclear**, or **Assessment unavailable**, as applicable. A service failure is not a low score.
- For each score, provide a short explanation and evidence linked to an actual learner turn. Naturalness/tone feedback can quote wording; audio feedback should describe an observed feature without inventing a quote or pronunciation error.
- Coaching reviews all completed turns, normally the 2–3-turn exchange, identifies a useful strength, and gives actionable advice on meaningful problems wherever they occurred. Notes connect each issue to the relevant turn and include improved wording or a delivery suggestion with its reasoning. Similar issues can be grouped. Do not invent a problem for every turn or limit review to the final answer.
- Spoken coaching summarizes the useful advice concisely and makes one improvement the retry priority. Model an alternative with a short explanation of why it helps; when the issue concerns stress, pacing, or tone, demonstrate that delivery aloud. The learner can ask about other feedback during coaching. Do not read all four numbers aloud by default.
- If the selected skill was already demonstrated, acknowledge it and offer a relevant refinement or transfer challenge. Do not manufacture an error to justify a retry.
- The normal path must support genuine assessment of all four dimensions when there is adequate speech. Permanent “unavailable” placeholders for audio dimensions do not satisfy the release requirement.

The technical specification must define how audio reaches an audio-capable evaluator, how the LLM judges evidence sufficiency per dimension, and how the rubric is checked against representative speech. Code can reject missing or corrupt input and invalid result structures, while the LLM decides whether usable speech supports a meaningful score. No fixed minimum seconds or word count automatically qualifies or disqualifies a sample. Scoring can adapt to the exchange while retaining the agreed dimensions, scale, evidence requirements, and unavailable states.

## 9. Content and completion details

### Content shape

Each purpose has a main expression, one alternative, a plain-English explanation of why it works and when it fits, and a short example. It also supplies a preset situation, learner/tutor roles, a communication goal, and a hint starter. **Listen** provides audible expression playback; **Practice** opens the corresponding scene.

Preset situations bound the context for the small Practice again variations described in section 5. Save the actual situation used with each session so Resume and Review retain its context.

Launch coverage includes nine purposes, exactly three in each scenario. Close a conversation and Ask for feedback extend the seven-purpose mockup; their expressions and practice content must be supplied for the release. There is no progression lock: learners can choose any available purpose. They may introduce their own details while speaking; a separate personalization form or custom-scenario builder is outside release scope.

| Scenario | Purpose | Preset situation |
| --- | --- | --- |
| Hosting a meeting | Welcome everyone | Open a weekly team meeting with colleagues. |
| Hosting a meeting | Set the agenda | Explain the goal and intended outcome of a project discussion. |
| Hosting a meeting | Wrap up | Close a team discussion and confirm decisions or next steps. |
| One-on-one | Share progress | Give a manager or colleague a concise project update. |
| One-on-one | Ask for support | Explain a blocker and make a specific request for help. |
| One-on-one | Ask for feedback | Ask a manager or colleague for specific feedback on a recent piece of work. |
| Casual talk | Start a conversation | Begin a friendly conversation with a colleague before work starts. |
| Casual talk | Follow up | Ask a colleague about a presentation they mentioned earlier. |
| Casual talk | Close a conversation | End a friendly chat with a colleague warmly when it is time to return to work. |

### Retry and takeaway

The completion behavior is:

1. Invite the learner to apply the main suggestion in a slightly varied prompt.
2. Finish after one response if it demonstrates the target, or use one relevant follow-up and finish after the second response.
3. Give brief spoken feedback on the targeted change. Acknowledge improvement only when the new response supports it; otherwise offer one concrete adjustment without requiring a passing grade.
4. Keep the original exchange's four scores labeled as that exchange's assessment. Do not automatically replace them with scores for the focused retry or show invented improvement deltas.
5. Offer another focused retry or Finish. Finish completes the session and opens its takeaway. The learner can also skip retry and finish immediately after the original coaching.

The takeaway identifies the practiced purpose, one expression to reuse, and the communication pattern or reasoning behind it. It can be heard aloud and read, and remains available with completed results until session expiry or deletion. It is not an independent saved-expression library. **Back to conversations** returns to scenario selection and preserves the completed session in Recent sessions.

## 10. Recovery and data lifecycle

### Session lifecycle

| State | Meaning and transitions |
| --- | --- |
| In progress | The learner is in roleplay, coaching, or an optional retry. Completing the 2–3-turn roleplay moves to coaching within the same session. |
| Paused | An unfinished session was paused, left, refreshed, or disconnected. Save its phase and completed work. Resume continues that phase. |
| Completed | The learner chose Finish. Preserve available results and the takeaway for Review. Practice again creates a new session rather than reopening the completed one. |
| Deleted or expired | Session content is unavailable and cannot be resumed or reviewed. Offer a fresh start. |

### Retention and recovery

- Temporarily store each guest session's selected purpose, actual practice situation, phase, progress, completed transcript, original assessment, coaching, retry feedback, and takeaway as available. Associate access with the same browser; no account is required.
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
| A02 | Learner selects any of the nine purposes | Scenarios appear in the order Hosting a meeting → One-on-one → Casual talk, each exposing exactly three purposes. Every purpose has an expression, alternative, explanation, audible playback, and matching practice entry, including Close a conversation and Ask for feedback. |
| A03 | Normal Q&A conversation | The tutor gives an audible setup and opening question or prompt, then produces follow-up questions grounded in the actual learner answers. Two learner answers count as two turns regardless of the number of tutor messages. Prepared sample playback cannot substitute for this check. |
| A04 | Goal achieved after 2 turns | The tutor can finish after the second learner answer at a natural break, acknowledge it, and switch explicitly to coaching without leaving a new question unanswered. |
| A05 | Goal not yet demonstrated after turn 3 | The tutor ends roleplay after the third learner turn and gives constructive coaching instead of adding a fourth roleplay question. |
| A06 | Learner pauses mid-answer | An ordinary thinking pause does not trigger an intrusive substantive reply. If completion is not detected when the learner is done, **I'm done** submits exactly once. The technical test plan must define representative audio samples. |
| A07 | Learner interrupts tutor speech | Playback stops and the exchange responds to the learner's new contribution; an obsolete response never resumes later. |
| A08 | Learner uses Pause, Mute, Hint, or replay | Capture/playback and turn counting follow the control table. No helper audio or incomplete answer is mistaken for an assessed learner turn. |
| A09 | Adequate clear speech | Four separate 1–5 scores reflect LLM judgment of the exchange with actual supporting evidence and explanations. Short, informative answers remain eligible based on that evidence. Spoken coaching identifies one retry priority; no aggregate grade appears. |
| A10 | Insufficient or unclear speech | Affected dimensions remain unscored with the right explanation. Silence and isolated acknowledgments never produce a fabricated full scorecard. |
| A11 | Focused retry | A slight variation elicits 1–2 learner turns. Feedback accurately addresses the targeted suggestion. The original exchange's scores stay labeled and unchanged; another retry or Finish is available. |
| A12 | Learner finishes early | Capture/playback stop. Feedback uses only completed work; no-completed-answer sessions do not claim achievement or invent scores. |
| A13 | Page refresh or lost connection | Recovery restores the saved phase and completed work, does not double-count turns, and requires an explicit action before microphone capture resumes. A partial answer is retried. |
| A14 | Provider or playback failure | The app follows the failure table, keeps controls usable, and never substitutes prepared successful responses or scores. |
| A15 | Session expiry or Delete | Session content is removed and cannot be resumed/reviewed. Back to conversations does not trigger deletion. Listing or reviewing completed sessions does not extend their retention. |
| A16 | Reviewer's clean checkout | Supplying the documented root `.env` and running Docker Compose starts the real frontend, backend, and Redis-backed voice experience. Required submission documents and video are present. |
| A17 | Learner leaves and resumes practice | Recent sessions shows the unfinished session. Resume restores its purpose, phase, and accepted turn count instead of restarting it. |
| A18 | Learner reviews completed practice and practices again | Review shows the completed transcript, original scores, feedback, and takeaway without microphone capture. Practice again creates a distinct session for the same purpose with a varied opening or small situation detail, answer-dependent follow-ups over a new 2–3-turn exchange, and a fresh assessment. The learner/tutor roles and intended difficulty remain consistent; the completed results stay unchanged. |
| A19 | Learner switches sessions | The previous unfinished voice session is paused and saved. Only the newly resumed session can capture or play live conversation audio. |
| A20 | Natural voice delivery | In a real conversation, tutor replies and coaching demonstrate natural phrasing, fluent rhythm, suitable intonation, and context-appropriate tone. A spoken expression example demonstrates the delivery discussed in coaching. Review uses actual generated speech; prepared mockup clips do not establish acceptance. |
| A21 | Useful feedback spans multiple turns | When distinct meaningful problems appear in separate learner turns, coaching can address both with evidence and actionable suggestions, including an issue from an earlier answer. Notes preserve the detail, spoken coaching stays concise, and the retry targets one priority. |

Visual acceptance uses the 390×844 app reference. In a shorter 375×667 browser viewport and desktop browser viewports, the app retains the same 390:844 aspect ratio, fits within the available area, and keeps content scrollable inside it. There is no alternate 375×667 app ratio or wide desktop layout. Verify readable text, touch targets of at least 44×44 CSS pixels, visible keyboard focus, transcript access, and reachable voice controls. Browser support, secure microphone access for physical phones, latency targets, and failure timeouts must be made concrete in technical design and the verification plan.

## 12. Deferred scope and next artifact

The release excludes native apps, separate desktop/tablet/landscape layouts, accounts, cross-device or long-term history, saved-expression libraries, streaks, leaderboards, aggregate grades, placement tests, bilingual instruction, an open-ended conversation mode, curriculum generation, and a custom-scenario builder. Temporary Recent sessions is included explicitly.

The provisional Good Company identity and Alex tutor name can carry over from the mockup for this release. They are reversible presentation defaults, not brand-development work. Preserve the mockup's voice emphasis, restrained palette, typography, and optional text without treating its simulated controls as implementation logic.

Once this product specification is reviewed, a separate technical specification should select the implementation and provider stack, define session state and audio assessment, establish measurable turn-taking and latency checks, and map these acceptance scenarios to verification. Product implementation has not started.
