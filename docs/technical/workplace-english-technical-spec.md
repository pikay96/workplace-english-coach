# Workplace English tutor — technical specification

Date: 2026-09-26

Status: technical design draft for review. LiveKit-only runtime credentials, the 60-second cue / 120-second answer cap, and wording-based MVP assessment are agreed. Fluency and Pronunciation scores are deferred beyond the MVP. No application code, provider configuration, Docker setup, or live model benchmark has been completed as part of this specification.

## 1. Scope and authority

Implement the learning journey in the [product specification](../product/workplace-english-product-spec.md): nine communication purposes, an LLM-generated spoken opening, an answer-dependent exchange of 2–3 learner turns, wording-based spoken coaching, optional 1–2-turn focused retries, and temporary guest history. Preserve the single portrait interface and voice-led experience.

The product specification owns learner-visible behavior and assessment anchors. The [assignment](../requirements/general-take-home-project.md) owns delivery requirements. The [domain glossary](../../CONTEXT.md) owns terminology. This technical specification resolves implementation choices; it does not replace these sources or turn the existing mockup into working software.

The design aims for a small, complete take-home submission. It uses one frontend, one Python backend codebase with separate API and agent processes, Redis, and LiveKit Cloud with LiveKit Inference. The interviewer supplies only LiveKit Cloud credentials; no separate OpenAI, Google, Deepgram, Cartesia, or other model-provider account/key is required. A locally generated cookie secret is application configuration, not another external account. Accounts, a database beyond Redis, durable learner recordings, a job-queue platform, and production autoscaling are outside the first implementation.

### Recommended decisions

| Area | Selection | Reason |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite; LiveKit browser SDK and React components | A client application is sufficient; the existing portrait design does not need server rendering. |
| Backend | Python 3.12, FastAPI, Pydantic, LiveKit Agents 1.8 release family | Typed state and assessment validation, async provider calls, and documented Python voice controls. Lock exact compatible versions during implementation. |
| Media service | LiveKit Cloud; run our agent locally in Docker | Avoid local WebRTC/TURN infrastructure while satisfying the assignment's containerized frontend and backend requirement. Internet access and LiveKit credentials remain necessary. |
| Conversation | LiveKit Inference `google/gemini-3.5-flash`, transcript input and validated text output | A catalog-listed, non-preview starting choice for contextual dialogue and tool/structured-result generation; benchmark quality and latency. [L2, L13] |
| Spoken output | LiveKit Inference `cartesia/sonic-3`, Blake voice `a167e0f3-df7e-4d52-a9c3-f949145efdab` | Speak validated conversation text, exact expressions, coaching examples, and recovered prompts with one catalog-listed voice. [L8] |
| Durable transcript | LiveKit Inference `deepgram/nova-3`, English streaming STT | Reuse final streaming transcripts for conversation and Redis; preserve application-owned answer boundaries. [L14] |
| Exchange assessment | LiveKit Inference `google/gemini-3.5-flash`, separate text request | Assess Naturalness and Workplace tone from the saved exchange and reliable wording; no learner audio or audio scores. |
| Answer duration | Gentle cue at 60 seconds; capture cap at 120 seconds | Preserve thinking pauses and let the learner submit the capped answer or retry; duration does not determine a score. |
| State | Redis, with atomic transitions and 24-hour activity-based expiry | Restore completed work independently of the browser, LiveKit room, and provider connection. |
| Learner audio | Bounded agent-process RAM during capture/submission only | Support streaming transcription and capped-answer submission; release accepted audio and assess saved wording. |
| Packaging | Four Compose services: `web`, `api`, `agent`, `redis` | One root `.env`, one build/start command, and explicit health checks. |

These are selected defaults, not claims that account access, latency, voice quality, or assessment quality have already been proven. Section 12 defines the checks that must pass before they are accepted for the release.

## 2. Voice architecture and model selection

### Approaches considered

| Approach | Advantages | Costs for this product | Decision |
| --- | --- | --- | --- |
| Streaming STT → text LLM → TTS through LiveKit Inference | One external credential set; controlled words and straightforward transcript recovery | Conversation and assessment cannot judge audible delivery cues | **Selected MVP architecture**, including a separate wording-assessment request. |
| Realtime audio input → controlled text → TTS through a direct provider plugin | Audible input cues and deterministic replay | The previously selected plugin needs separate provider credentials | Excluded by the interviewer's setup constraint. |
| Direct speech-to-speech through a direct provider plugin | Expressive native audio output | Separate provider credentials; less control over exact words before playback | Excluded by the interviewer's setup constraint. |

The selected pattern is a **STT–LLM–TTS pipeline**, replacing the earlier half-cascade proposal. LiveKit Inference supplies the three model roles and manages their usage through LiveKit Cloud. A locally hosted agent can use that service; this does not require deploying our agent to LiveKit's agent-hosting platform. Do not confuse a model provider's LiveKit plugin with access through LiveKit Inference. [L1, L2, L7]

### Provider responsibilities

The conversation LLM interprets the learner's transcribed contribution, the communication goal, and the appropriate next utterance. It receives the selected content, saved situation and roles, authoritative phase and turn budget, and the short conversation history. It does not receive acoustic cues and cannot claim to hear pronunciation, intonation, or hesitation. Request a typed proposal through the supported tool/structured-result interface and always validate it with Pydantic before applying it. Verify exact model options against the pinned SDK; do not copy direct-provider settings into Inference without checking support. [L13]

The streaming transcription model supplies durable wording. It is not the pronunciation judge. Preserve filler words, disable semantic rewriting/entity normalization, and do not boost the taught expression in a way that biases recognition toward the expected answer. Aggregate final transcript segments against the application's capture boundaries; an interim or final STT event is not itself a completed learner answer. Reuse the same final wording for the conversation request and Redis. Do not introduce a separate file-transcription API/key. [L14]

The TTS model speaks only server-approved text. Use concise, conversational English at a comfortable B1–B2 pace. Roleplay delivery follows the workplace relationship; coaching uses a supportive explanatory tone. Use only the speed/emotion controls documented for the selected Inference model; do not assume free-form delivery instructions are supported. Blake is an initial catalog voice, not a tested quality claim. Learner-facing listening tests remain necessary. [L8]

The wording evaluator uses a separate Inference LLM request with all accepted original answers, transcript reliability, and conversation context. It returns Naturalness and Workplace tone results, transcript-linked evidence, coaching notes, and one wording-focused retry priority. Reusing the conversation model identifier does not reuse its live prompt, tools, or mutable context. The evaluator has no room, microphone, playback, or session-lifecycle tools.

All remote model calls must authenticate through LiveKit Cloud. Model identifiers and voice are configurable in the root `.env`; no direct-provider fallback is allowed. LiveKit Inference has usage-based billing, so a LiveKit project with sufficient inference access/credit is required. Its documented zero-data-retention policy applies to Inference traffic; recording/observability controls remain separate. [L2]

### Deferred audio assessment

The user chose to simplify the MVP to wording-based feedback and revisit audio scores later. Do not render Fluency or Pronunciation cards, infer speaking quality from STT confidence/word counts, or describe the assessor as hearing audio. Label results **Based on your words**; Workplace tone concerns word choice, directness, and formality.

The checked Python Inference client serializes its chat context using an OpenAI-compatible format whose converter skips `AudioContent`. A model's audio capability in its native API does not establish audio-input support through this route. Any future audio-scoring feature needs a verified audio-capable path and a new calibration/data-lifetime design. It is outside this release, not an unresolved MVP dependency. [L16]

### Cost and compatibility

Record usage by Inference model, response duration, and retries without recording learner content. Calculate actual cost per completed practice session from dated LiveKit Inference prices; include STT, conversation LLM, assessment LLM, TTS, and transport separately. Do not estimate a flat cost per minute from text-token prices. A model-catalog entry is not proof of access, performance, or assessment quality. [L2]

Pin Python and JavaScript dependencies in lockfiles and pin container image versions/digests when creating the implementation. Store the selected model identifier, prompt version, rubric version, and content version with each session/result. The checked model pages do not establish an immutable dated snapshot for every selected alias, so do not invent snapshot names. Model changes rerun the voice and assessment checks.

## 3. Components and data flow

```mermaid
flowchart LR
    B[Portrait browser app] -->|HTTPS: sessions and controls| API[FastAPI session API]
    API -->|SSE: versioned state| B
    API <--> R[(Redis: text and state)]
    B <-->|WebRTC audio| LK[LiveKit Cloud]
    LK <-->|WebRTC audio| A[Python agent job]
    API -->|Explicit room dispatch| LK
    A <--> R
    A -->|Learner audio| STT[LiveKit Inference STT]
    STT -->|Final transcript segments| A
    A <-->|Transcript in, turn proposal out| LLM[LiveKit Inference LLM]
    A -->|Validated words| TTS[LiveKit Inference TTS]
    TTS --> A
    A -->|Saved exchange wording and context| E[LiveKit Inference wording evaluator]
    E -->|Two dimensions and coaching| A
```

The API and agent share a small domain package rather than call each other's internal implementation. Redis is the source of truth. LiveKit events describe transport and speech activity; they do not own product progress.

| Module | Responsibility and interface | Dependencies |
| --- | --- | --- |
| `content` | Read nine versioned purpose definitions; validate scenario order, expressions, roles, and situation constraints | Curated JSON; no model or Redis dependency |
| `sessions` | `create`, `resume`, `apply_command`, `get`, `list`, `delete`; ownership, expiry, idempotency, and state transitions | Redis repository and trusted server clock |
| `conversation` | Apply a validated turn proposal to the current phase and budget; construct phase-specific model context | Typed session/content objects; no browser or SDK types |
| `voice` | LiveKit connection, audio segmentation, Inference adaptation, interruption, and playback receipts | LiveKit SDK/Inference, session interface |
| `assessment` | Build a transcript evidence manifest, call the wording evaluator, validate results, and generate targeted retry feedback | Saved exchange, typed rubric, LiveKit Inference LLM |
| `api` | Cookie authentication, request validation, endpoints, SSE, explicit dispatch, and redacted operational errors | Session interface and LiveKit server API |
| Frontend session controller | Render state, own capture/playback, apply immediate local stops, and reconcile versioned server events | API/SSE and browser LiveKit SDK |

Use one active LiveKit `AgentSession` per connected practice session. Roleplay, coaching, and focused retry have separate prompt/context builders and allowed actions inside that job. This is a small phase workflow, not separate deployed services or several agents talking at once. The evaluator is a bounded task and cannot control the microphone, room, or session lifecycle.

Project model context from the canonical session: approved tutor words with their delivery status, accepted learner answers, current phase, and remaining budget. Remove abandoned proposals and canceled questions. On recovery, rebuild this context from Redis; do not load a serialized provider session or pretend a partly played utterance was fully heard. Treat learner speech, transcripts, and quoted examples as task data, never as instructions that can change the rubric, ownership, or turn limits.

Suggested source layout:

```text
frontend/src/{app,features,voice,api}
backend/app/{api,sessions,conversation,voice,assessment,content}
backend/tests/{state,contracts,agent,audio}
content/workplace-english.json
compose.yaml
.env.example
PROMPT.md
README.md
workflow.md
```

## 4. Content, opening generation, and phase flow

### Content schema

Each purpose contains `scenario_id`, `purpose_id`, display order, title, main expression, alternative, explanation, example, hint starter, preset situation, learner role, tutor role, communication goal, difficulty, and allowed small situation variations. Validate exactly three purposes per scenario and the product's scenario order. Curated examples guide learning; they are not prepared conversation responses.

For a new session, the conversation LLM produces a structured `OpeningProposal` containing the actual situation, role-consistent setup, and one opening question or prompt. Save the validated proposal before speaking it. Practice again passes the earlier opening as variation context and requests different wording or a small permitted situation change. If the new opening is an exact normalized duplicate, retry generation once; a repeated failure is visible and retryable, not replaced with a prepared successful opening. No global uniqueness database is needed.

Resume uses the saved situation and question. It does not call opening generation again.

### Normal phase flow

```mermaid
stateDiagram-v2
    [*] --> Roleplay: Start and save generated opening
    Roleplay --> Roleplay: Accepted learner turn 1
    Roleplay --> Coaching: Turn 2 and goal demonstrated
    Roleplay --> Roleplay: Turn 2 and another follow-up useful
    Roleplay --> Coaching: Turn 3, regardless of goal
    Coaching --> Retry: Learner chooses focused retry
    Retry --> Retry: First answer needs a follow-up
    Retry --> Coaching: Target demonstrated or answer 2
    Coaching --> Completed: Finish
    Roleplay --> Completed: Finish early
    Retry --> Completed: Finish
```

Pause is a lifecycle overlay that preserves the current phase; it is not a new roleplay phase. Completing roleplay does not complete the practice session.

### Turn proposal and commit

1. Allocate a server-side `input_id` for the current capture buffer. Automatic completion and **I'm done** compete to seal that same buffer; only one can win.
2. Seal the learner-only audio segment. Finalize the streaming transcript for that capture boundary and request an Inference LLM `TurnProposal`. Disable automatic unconstrained spoken responses: the proposal must pass the controller before TTS receives text. A duration-capped buffer first waits for the learner's explicit submission choice, as defined in section 5.
3. The proposal describes `contribution_kind` (`answer`, `help`, `coaching_question`, `unusable`), `relation` (`new_answer`, `continuation`), contextual goal/target judgment, acknowledgment, and the proposed next action and words. The server supplies permissible reference IDs; the model cannot create session IDs, turn numbers, epochs, or ownership facts.
4. For an answer, wait for the final transcription result or an explicit unclear-speech result. A provider failure is a retryable pending submission, not fabricated wording. Validate the proposal against the phase and the prospective count, then atomically save the accepted answer, transcript status, next prompt/phase, and response record.
5. Only after that commit may the tutor acknowledge the answer aloud. The frontend shows a submission as saved only after the matching receipt. A browser loss before receipt is reconciled by `input_id`, never by assuming the answer was lost or accepted.
6. Publish the approved text through TTS, with a new `playback_id`. Record whether playback completed, was interrupted, or failed. Generated words and words confirmed played are distinct facts.

The LLM decides whether a contribution answers the question or is a request for help; code does not use keywords or phrase matching to make that judgment. Silence and technical corruption can be rejected before model evaluation. A genuine brief or unclear spoken answer can count while still providing insufficient evidence for one or more scores.

The controller enforces the numeric limits. Before learner turn 2, the normal next action is one follow-up. After turn 2, the model's contextual goal judgment selects a follow-up or coaching. After turn 3, only acknowledgment and a coaching transition are allowed. The structured closing form has no follow-up field. Invalid proposals get one bounded regeneration with the permitted action; they are never spoken first and repaired afterward.

The final roleplay acknowledgment and coaching bridge are short. The visible phase changes with the committed transition; a labeled assessment-pending state is allowed while the score request runs. The first coaching summary reviews useful evidence across the exchange, models an alternative, and identifies one retry priority. Detailed notes retain all distinct meaningful issues rather than only the last learner answer.

Coaching questions stay in coaching. A focused retry has its own ID and 1–2-answer budget, a small situation variation, and the selected target. Its evaluator returns targeted wording feedback against the original suggestion; it does not replace the original two scores. No automatic success or improvement delta is generated.

## 5. Turn-taking, capture, and playback

### LiveKit and provider integration

Use explicit dispatch with a named agent and metadata containing only `session_id`, `guest_id`, and `connection_epoch`. On job entry, fetch and authorize the Redis snapshot instead of trusting the dispatch metadata as session content. Explicit dispatch and container-hosted agent jobs are documented LiveKit paths. [L6, L7]

Use Silero VAD and LiveKit's text-based `MultilingualModel` turn detector with English STT as the initial completion detector. The detector uses conversation context to distinguish a pause from completion and can run locally on the CPU for custom agent deployments. Bake its assets into the agent image. Tune endpointing against the specified thinking-pause fixtures; STT chunk finalization must not independently commit answers. Local speech activity detection also stops TTS promptly on learner interruption. [L14, L15]

The adapter must map streaming transcript segments and measured audio boundaries to application `input_id` values. **I'm done** submits the still-open buffer; it is a no-op for an empty or already submitted buffer. It must suppress a later duplicate end-of-turn event. Cap confirmation is a distinct sealed-but-unsubmitted state, not an already accepted answer.

LiveKit documents `interrupt`, clearing input, manual commit, enabling/disabling audio input, and the `on_user_turn_completed` hook for agent-side turn detection. Route completion through the application controller and its validated proposal path; suppress the default response path if a custom path generates the proposal. Confirm the hook, transcript-boundary mapping, and single-response behavior against the pinned SDK in the first integration check. [L3, L4]

Disable speculative/preemptive generation and automatic resumption after false interruptions for the initial release. The latest documented defaults can enable these behaviors, which conflicts with this product's careful turn completion and obsolete-speech rules. An intentional stop cannot trigger automatic replay later. [L3, L9]

### Agreed answer-duration policy

- Start the server-authoritative monotonic timer at the first detected learner speech, not when the microphone opens or the prompt starts. Include thinking pauses inside the answer. Natural completion and **I'm done** can submit earlier.
- At 60 seconds, show a gentle **Wrap up your answer** cue once. Keep listening; do not speak over the learner or introduce a mandatory countdown.
- At 120 seconds, stop capture and seal the buffer as `awaiting_limit_confirmation`. Preserve it in agent RAM and show **Use this answer** / **Try again**. Do not automatically count, assess, or discard it. Explicit submission uses the ordinary idempotent input transaction; retry discards the candidate and returns to the same prompt with capture enabled only by that user gesture.
- Count continuation segments toward the same logical answer's remaining budget, excluding tutor playback time between capture intervals. A premature detector boundary must not reset the answer allowance. Keep the latest accepted revision until a replacement is atomically submitted; an abandoned continuation cannot erase accepted work.
- A capped answer submitted with **Use this answer** carries a `capture_limited` flag. Evaluate the captured evidence without penalizing the technical cutoff or claiming the learner finished a thought they did not finish. A short answer remains eligible; neither threshold is a scoring criterion.
- Pause, Mute, Hint, replay, navigation, disconnect, Delete, or expiry clears a still-unsubmitted capped buffer under the normal audio-lifetime rules. Recover the same prompt with an explanation when its RAM is lost. Never claim an unsent capped answer was saved.

LiveKit's `user_turn_limit.max_duration` and `on_user_turn_exceeded` offer turn-limit hooks, but the SDK counter resets when the agent starts speaking and its default hook generates a spoken interruption. Our application answer clock and buffer state are authoritative. Override/suppress the default interruption if using that hook; no tutor utterance may bypass the capped-answer choice or reset a continuation budget. [L3]

### Interruptions and premature completion

Speech during tutor playback stops the current output immediately and opens a learner capture buffer. It is eligible learner input, unlike a Pause or Hint fragment. An interrupted tutor message is retained with its delivery status; neither the model nor the UI should claim its full contents were heard.

If completion was detected before the learner finished the same answer, the model can classify the new segment as a continuation of the latest answer. While that tutor response is being generated, played, or interrupted, merge the segments under the same `turn_id`, increment its `answer_revision`, cancel the obsolete response, and recompute the next action. Do not increment the accepted-answer count. Any assessment based on the older exchange revision is rejected.

The transition into coaching remains interruptible. A continuation that interrupts the premature coaching bridge reopens the latest answer and invalidates that provisional transition. Freeze the exchange once the bridge reaches terminal delivery with no continuation being processed: completed playback, or failed playback with output canceled. An explicit Pause, navigation, or Finish can also settle an already committed coaching transition using only accepted answers. Playback failure must not block assessment forever. After freezing, new speech is a coaching question or clarification rather than an additional original roleplay answer. This makes the continuation boundary explicit and testable.

### Control effects

| Control/event | Immediate local effect | Server effect |
| --- | --- | --- |
| Start / Resume | On this user gesture, unlock audio; request microphone access only after the previous session's capture has stopped | Claim the guest's active voice ownership, connect, and continue the saved phase; enable publication only after the claim is confirmed |
| I'm done | Seal the current buffer once; show processing | Submit the same `input_id` used by automatic completion |
| 120-second answer cap | Stop microphone capture; keep the answer choice visible | Retain sealed audio in RAM without accepting or assessing it |
| Use this answer / Try again after cap | Explicitly submit the capped answer, or discard it and reopen the current prompt | Resolve the same pending input once; record `capture_limited` on submission and preserve accepted work on abandonment |
| Pause | Stop microphone track, detach/flush playback, discard unsubmitted audio | Save paused lifecycle and phase; invalidate conversation work and output |
| Mute | Stop microphone track and discard the current unsubmitted fragment; leave tutor playback running | Disable input, preserve completed answers and pending tutor output |
| Hint | Stop normal capture/playback; show paused practice | Save pause; generate/play one separately labeled helper utterance; require explicit Resume |
| Hear Alex | Suspend capture and discard an unfinished fragment; play the saved last tutor words | No new conversation turn; restore listening only if it was previously active and the same ownership is still valid |
| Finish | Stop capture and existing conversation playback | Freeze submitted work, mark completed, and create/retain available results and takeaway |
| Back / switch session | Stop capture/playback before navigation | Pause unfinished work; fence the old connection before activating another |
| Disconnect / refresh / background suspension | Stop media and clear partial input as soon as detected | Invalidate the live connection; preserve accepted work; restore unfinished work paused |
| Delete / expiry | Stop media and clear displayed content | Remove session content, terminate its room/job, and reject every later write |

A paused session can play an explicitly requested hint or replay. This is a narrowly scoped playback permission associated with that command; it does not authorize a pending roleplay response. A completed session can play saved feedback/takeaway on request without requesting microphone access. Finish can present its newly requested feedback/takeaway only while that view remains current; nothing may autoplay after navigation.

Connected conversation and replay use LiveKit audio. Expression exploration and completed-session Review use a same-origin streamed HTTP audio response from the same TTS adapter, so they need neither a room connection nor microphone permission. One frontend playback controller owns both transports and cancels either when navigation, another playback request, or a voice session takes ownership. Do not store or cache personalized generated audio.

Capture and playback permissions are checked separately. Show words does not change either. Keep controls usable in connecting, thinking, and assessment-pending states. State labels are text, not animation alone.

## 6. Session state and API contracts

### Durable session record

| Field group | Stored values |
| --- | --- |
| Identity | Server-generated `session_id`, owning `guest_id`, `schema_version` |
| Content | Purpose/content version, actual situation, roles, goal, generated opening, optional source-session ID for Practice again |
| Lifecycle | `in_progress`, `paused`, or `completed`; phase `roleplay`, `coaching`, or `retry`; current substate |
| Ordering | `revision`, `connection_epoch`, `generation_id`, last event sequence, idempotent command receipts |
| Conversation | Current question ID/text; accepted answer IDs and revisions; submitted transcript and reliability state; tutor messages and delivery state |
| Pending work | Sealed input ID and status, including `awaiting_limit_confirmation`; capture duration / `capture_limited` metadata; response request ID and causal answer revision; assessment request ID and frozen exchange hash |
| Assessment | Two dimension results, transcript evidence, notes, retry priority, model/prompt/rubric versions, availability reasons |
| Retry/takeaway | Retry IDs and completed turns/feedback; reusable expression and reasoning; text needed for playback |
| Recovery | Saved phase, capture preference, text-visibility choice, interrupted-fragment notice, previous delivery status |
| Time | `created_at`, `last_practice_at`, `expires_at`, `completed_at` when applicable |

Audio bytes, base64 audio, provider secrets, and serialized SDK/provider sessions are never fields in this record. A pending-input availability marker is advisory and identifies its live worker owner; it cannot make a lost unsubmitted buffer recoverable. Accepted transcripts suffice for wording assessment.

The accepted count is derived from distinct accepted roleplay answer IDs, not from the number of transcript messages, audio chunks, callbacks, or model calls. Retry counts are derived independently.

### Ownership and persistence

Issue a random high-entropy guest identifier in an HttpOnly, SameSite=Lax cookie, authenticated with a locally generated server secret. Set Secure on HTTPS. A 30-day browser identifier may outlive session content; it does not extend any session's 24-hour retention. Session IDs are random, and every API operation checks the guest association. Redis and privileged LiveKit credentials are never browser-accessible.

Use one Redis key per session, a guest Recent sessions index, and a guest active-voice lease. Use a shared guest hash tag in key names so related atomic operations can remain in one Redis Cluster slot if sharding is introduced later.

The API and agent call the same atomic transition functions, implemented with Lua or WATCH/MULTI. Each write checks key existence, expiry, owning guest, relevant revision, and operation ID before replacing state. A failed expectation returns the current state or a conflict; it never overwrites it. All mutation paths, including worker results, must preserve the existing absolute expiry unless they represent eligible new practice activity.

Commit operation intent before making a provider call, then conditionally commit its result. Never hold a Redis transaction or state lock across network generation, playback, or assessment. Retried commands return the original receipt and do not renew retention twice. Expiry and Delete take precedence even if the underlying provider request is still running.

Maintain a 15-second active-voice lease, renewed every 5 seconds while the foreground connection is healthy. Lease heartbeats are not practice activity. A connection uses a fresh random epoch; late workers cannot regain ownership. A new session switch fences the previous connection and removes its media participant before allowing the new publisher. If removal/ownership cannot be confirmed, remain connecting with capture off.

Use a browser tab lock where available and BroadcastChannel for immediate cross-tab coordination. Redis ownership and room authorization provide the authoritative check. On a lost control connection, clients fail closed and stop media instead of relying on an indefinitely valid WebRTC connection.

For the take-home, run Redis without RDB snapshots or AOF and without a data volume. This avoids old transcript copies surviving expiry in persistence files. Refresh, browser reconnect, API restart, and agent restart recover while Redis survives. **Redis process/data loss loses temporary history**; explain the unavailable session and offer a fresh start. Stronger infrastructure recovery would require an explicit persistence and deletion policy, not an unmentioned disk backup.

### API surface

All session endpoints are same-origin and cookie-authenticated. Validate Origin on mutations. Use typed errors and `Cache-Control: no-store` for session content. No learner answer is uploaded through a generic public HTTP audio endpoint.

| Endpoint | Contract |
| --- | --- |
| `GET /api/content` | Return the nine curated purpose definitions and content version |
| `POST /api/guest` | Establish browser identity; no microphone or practice session |
| `GET /api/sessions` | List owned, unexpired sessions; clean stale index entries without renewing retention |
| `POST /api/sessions` | Create from a purpose and optional prior session for Practice again; idempotency key prevents duplicate starts |
| `GET /api/sessions/{id}` | Return snapshot, availability, revision, and expiry; no automatic resume |
| `POST /api/sessions/{id}/connect` | Explicit Start/Resume; claim ownership and return a short-lived room-scoped token and current epoch |
| `POST /api/sessions/{id}/commands` | Apply Pause, Resume, Mute, Unmute, I'm done, capped-answer submit/retry, Hint, Replay, focused retry, Finish, or retry of a failed operation |
| `GET /api/sessions/{id}/events` | SSE with event sequence and full-state resynchronization when needed |
| `POST /api/sessions/{id}/heartbeat` | Renew only the matching voice lease; never renew session retention |
| `POST /api/sessions/{id}/playback` | Authorize playback of a saved tutor message/coaching/takeaway by ID; server resolves the words |
| `DELETE /api/sessions/{id}` | Idempotently remove owned content and fence active work |
| `POST /api/content/{purpose_id}/playback` | Generate audio for a curated expression/example without microphone capture |

Commands include `command_id`, `expected_revision`, and `connection_epoch` when acting on live media. Voice controls reach the agent via a Redis notification, with the saved state as authority; delivery loss is repaired by reading that state. LiveKit RPC may carry a low-latency duplicate notification using the same command ID, not a separate mutation path.

An event includes `session_id`, `revision`, `sequence`, `connection_epoch`, `type`, and a bounded payload. Events are hints to reconcile state; Redis Pub/Sub is not durable history. After SSE reconnect or an event gap, fetch the snapshot. Reject events from other sessions or old epochs. A completed-session review never calls the connect endpoint.

LiveKit tokens grant access only to the server-selected room/identity, subscription to tutor audio, and publication of the microphone. They do not grant room administration or camera/screen publication. Use a five-minute initial token lifetime. Token expiry alone does not terminate an existing or reconnecting participant; explicitly remove/revoke stale participants and use new room/identity epochs during recovery. [L10]

## 7. Transcription evidence and wording assessment

### Audio path and lifetime

Subscribe to the authorized learner microphone track in the agent and obtain PCM frames through LiveKit's raw audio stream interface. Feed streaming STT and a bounded current-answer buffer from this learner source. Never transcribe a mixed room track: tutor speech, expressions, hints, and replays are excluded by source and capture state. Browser echo cancellation is enabled; detected speaker leakage or recognition ambiguity is treated as transcript uncertainty. [L5]

Use mono PCM16 at 16 kHz for the current-answer buffer, resampling appropriately for the configured STT interface. Track source identity, capture intervals, and transcript segment IDs under `input_id`. Preserve actual ordering and uncertainty; do not rewrite recognition results to resemble the taught expression. The assessor receives transcripts, never PCM, WAV, or audio references.

The answer cap is 120 seconds under section 5, with an 8 MiB application-owned audio-buffer budget per active session, including encoding/copy headroom. A full 120-second PCM16 mono buffer at 16 kHz is 3,840,000 bytes. SDK buffers also need bounded queues and measured memory use. Do not accumulate completed-exchange audio. Unexpected resource exhaustion stops capture with an explicit retryable capture error and no automatic submission.

Discard unsubmitted fragments immediately on Pause, Mute, Hint, replay, navigation, or loss of capture. Release a submitted answer's audio after its final transcript and acceptance receipt are saved; assessment does not depend on that audio. Hold a capped unsubmitted candidate only while its live session remains active and until submission, retry, a discard event, or expiry. Delete/job shutdown frees all buffers. A pending wording assessment can finish or be retried from Redis independently of audio lifetime, but cannot start unauthorized playback.

Do not use MediaRecorder persistence, IndexedDB audio storage, filesystem temporary WAVs, Redis audio blobs, LiveKit Egress, or provider Files API uploads. Raw frames elsewhere in SDK histories/caches must be released too. Disable core dumps and do not deliberately use disk-backed audio spooling; host-level swap is an infrastructure property, not a promise of cryptographic memory erasure.

### Assessment input

The request contains the two-dimension product rubric, purpose/actual situation/roles, original tutor context, every accepted original learner turn and revision, transcript reliability, and any `capture_limited` flags. Ask the evaluator to assess meaning and wording rather than exact expression reproduction. State that audio is unavailable and that no delivery, fluency, pronunciation, confidence, stress, or vocal-tone claim is permitted. A capped answer is judged only on supported wording without penalizing its forced ending.

Use a standalone `inference.LLM` request with `ASSESSMENT_MODEL`, an isolated chat context, and a typed assessment-result schema/tool. Validate the complete result with Pydantic and reference checks before saving it. Do not depend on a model's schema support to establish factual correctness. The call authenticates using LiveKit credentials and returns data only; it has no application-effect tools. [L13]

### Result schema

| Field | Rule |
| --- | --- |
| `exchange_id`, `exchange_revision`, `rubric_version` | Must match the frozen request; server attaches authoritative IDs |
| `dimensions` | Exactly `naturalness`, `workplace_tone`; reject audio-dimension fields |
| Per dimension `status` | `scored`, `not_enough_detail`, `transcript_unclear`, or `assessment_unavailable` |
| Per dimension `score` | Integer 1–5 only for `scored`; otherwise null |
| Per dimension `basis` | Always `wording`; visible explanation states the assessment's basis |
| Per dimension `explanation` and `evidence` | A useful explanation and at least one real original-turn reference for each score |
| Evidence entry | Original turn ID and answer revision, wording observation, and an optional exact transcript quote; suggestions are separate fields |
| `strengths`, `issues` | Evidence-linked observations; each issue includes a concrete suggestion, example, and reason |
| `retry_priority` | One actionable issue or supported refinement/transfer challenge, linked to the notes |
| `spoken_summary`, `modeled_example`, `takeaway` | Short spoken coaching and reusable learning content grounded in the exchange |

The LLM decides whether reliable wording is sufficient for each dimension. Code validates the schema, evidence IDs/revisions, quote provenance, and transcript availability. It rejects audio bases/dimensions and unresolved evidence. Semantic checks and human review verify that free-text comments do not invent delivery observations; schema validation alone cannot prove that. Code does not assign scores from word counts, STT confidence, duration, a keyword checklist, or hidden per-turn grades.

Transcription remains fallible. Do not instruct STT to correct the learner's grammar or expand unclear words. Preserve recognized text and uncertainty separately. The evaluator cannot check it against audio or assert a recognition mistake as fact. Treat unclear or contradictory wording cautiously, withhold unsupported scores, and ask for clarification within the remaining turn budget. A later coaching clarification does not silently rewrite original scores. No recognition mismatch is a pronunciation error.

Naturalness and Workplace tone use reliable wording and context. Tone explanations may discuss the politeness or directness of a quoted phrase, but cannot claim intonation or warmth of delivery. Silence or isolated acknowledgments cannot produce a fabricated complete scorecard. The two scores are never averaged into an overall grade.

If a model response is malformed or references nonexistent evidence, retry once with the validation errors and the same evidence. Never silently coerce a score or invent a quotation. Valid independently supported dimensions may be preserved; failed dimensions remain unavailable. Surface **Not enough detail**, **Transcript unclear**, or **Assessment unavailable** accurately.

### Recovery and immutability

Freeze the original exchange only after its final answer/continuation boundary has resolved. Store a hash of its answer IDs, answer revisions, and context. Assessment writes require the same hash and request ID, a still-existing session, and a valid expiry; they do not require the learner to remain on the feedback page.

A successful original score is immutable. A retry of an unavailable assessment may fill missing dimensions from the saved original transcript, but does not overwrite already obtained scores. Focused retry transcripts belong to a separate targeted evaluation and can never fill gaps in the original exchange.

After worker restart, reconstruct the pending assessment from the frozen Redis exchange. Start one replacement request under a new attempt ID; stale attempt results fail the conditional write. Resume assessment independently of microphone activation. If Redis data is lost, do not recreate the exchange. Loss of raw audio does not invalidate saved wording or its assessment.

If Finish is pressed before any accepted answer, complete the session with no scores and a clearly labeled expression reminder, without claiming achievement. If accepted work exists, Finish freezes only that work, permits bounded assessment/result completion, and preserves any available feedback. A partial in-progress answer is excluded.

## 8. Recovery, cancellation, and retention

### Two kinds of cancellation

**Conversation work** is fenced by connection epoch, generation ID, and the causal answer revision. Pause, navigation, session switch, interruption, or deletion invalidate its right to publish speech. Abort the provider/TTS request when possible and reject late chunks/results even when upstream cancellation arrives too late. Check the fence before committing a response and before publishing each audio batch.

**Assessment work** is fenced by session existence/expiry, request ID, and frozen exchange hash. It can finish while the learner is paused or reviewing another screen, since completed results should be saved. It cannot autoplay, renew retention, revise a different exchange, or recreate a deleted/expired session.

The browser also owns a local playback generation. Any stop action detaches or flushes its audio output immediately, before waiting for the server. A later event cannot attach audio unless its session, connection epoch, and playback ID remain authorized. Clear the server audio queue too; after cancellation, establish a fresh output track if the pinned SDK cannot guarantee that queued frames from the previous generation are discarded. Verify this rather than assuming a canceled HTTP request flushes WebRTC playback.

### Recovery table

| Saved condition | Recovery behavior |
| --- | --- |
| Capturing an unfinished answer | Discard the fragment; show the same current prompt and accepted count, paused |
| Capped answer awaiting submission choice | Preserve the candidate only with its healthy live owner; otherwise discard it and return paused to the same prompt with an explanation |
| Sealed input without accepted receipt | Reconcile by input ID; finish its commit if a live owner still has the evidence, otherwise report it was not saved and repeat the prompt |
| Accepted answer, no committed tutor reply | Keep the answer; explicitly resume/retry generation once from saved context and the same response operation |
| Tutor reply committed, playback incomplete | Preserve its words and interrupted/unknown delivery state; offer/replay those words on explicit Resume without generating a new question |
| Assessment pending, saved transcript available | Allow bounded completion or retry from the frozen Redis exchange, including after worker restart |
| Coaching/retry paused | Restore that phase and its current question/target; do not restart roleplay |
| Completed | Read-only review with optional audio playback; Practice again creates another session |
| Deleted/expired/missing Redis data | Return an unavailable-session screen and fresh-start action; never recover fabricated history |

Treat LiveKit reconnecting/disconnected events, SSE loss, page unload, and mobile background suspension as reasons to stop capture/playback. Unload delivery is best effort; lease expiry and worker disconnect detection repair missed pause commands. A snapshot of an unfinished session with no valid live owner is normalized to paused before Resume is offered. No automatic microphone reacquisition occurs.

### Expiry algorithm

`expires_at = last_practice_at + 24 hours`, using the server clock. Eligible activity is starting/resuming practice, accepting a learner contribution, requesting active help/coaching/retry, and the first successful Finish. Replay of a saved completed result, reading, listing, passive media/lease heartbeats, and background model completion do not renew the interval. A replay used as active practice help can renew it only while the session is unfinished.

Set Redis expiry from the same absolute timestamp on all session-owned data. Recent sessions entries are indexed by activity and carry expiry; filter missing or expired records and prune stale index entries on reads. Redis expiry plus a periodic sweeper releases active rooms/work and stale references. Every read/write checks `expires_at` as well, so correctness does not depend on keyspace notifications or sweeper timing.

Delete atomically removes the session and Recent sessions reference, fences its active connection, and cancels work. A result writer uses update-if-present semantics; it never creates a missing key. No content-bearing tombstone is needed. Unknown/foreign IDs do not reveal whether another guest's session exists. An owned stale reference may explain expiry; all other unavailable IDs use a neutral message.

## 9. Browser behavior and failure budgets

### Supported environment

Release verification targets current stable Chrome and Edge on desktop, Chrome on Android, and Safari on iOS, with exact tested versions recorded in the README. Other browsers receive capability-based microphone/audio errors rather than an invented connected state. Physical-device testing is required; responsive desktop emulation is insufficient for microphone permission and audio-unlock behavior.

Serve through HTTPS for physical phones. `http://localhost:8080` is the documented local-desktop path; a phone accessing an HTTP LAN IP does not get the same secure-context treatment. For a phone demo, use a trusted HTTPS reverse proxy/tunnel to the Compose web service, configure `APP_ORIGIN` and secure cookies, and verify WebRTC connectivity from that phone. This is optional network setup around the same containers, not a separate app implementation.

Compute the app bounds as `width = min(390px, available_width, available_height * 390 / 844)` and `height = width * 844 / 390`, using the dynamic viewport and accounting for outer insets. Reflow/scroll inside these bounds. Do not scale the whole DOM with a transform: type and controls retain readable sizes and at least 44×44 CSS-pixel targets. Test the 390×844 reference, a 375×667 host, a narrow phone, and a wide desktop.

### Initial measurable targets

These are release targets to measure, not observed results. Measure on a stable broadband connection from the actual demo region, with a warmed agent and cached assets; report cold-start numbers separately.

| Measurement | Target / action |
| --- | --- |
| Start click to first audible generated opening, excluding human permission delay | p95 ≤ 8 seconds; connection attempt fails visibly at 15 seconds |
| Detected completed answer to first audible substantive response | p50 ≤ 1.8 seconds, p95 ≤ 3.5 seconds over at least 30 replies |
| Last speech frame to reply for clearly finished audio samples | p95 ≤ 5 seconds; measure endpointing separately from generation |
| Pause/Mute/Finish local capture stop | ≤ 150 ms after the control event |
| Intentional barge-in to tutor silence | p95 ≤ 300 ms; no later resumption of obsolete audio |
| Feedback after the final answer | Short acknowledgment/bridge within reply budget; full assessment p95 ≤ 12 seconds |
| Assessment request | 30-second total deadline including at most one retry; visible unavailable state afterward |
| Transcription / turn proposal / TTS start | 8-second deadline per operation; no hidden indefinite SDK retries |
| Explicit Resume to restored ready state | p95 ≤ 5 seconds, excluding permission dialog |
| Lost connection/ownership | Local stop on detection; server lease repair within 15 seconds |

At 3 seconds without a reply, show truthful processing text. At an operation deadline, expose Retry and exit controls. A partial audible response is never automatically replayed as a whole on a network retry. Upstream request cancellation does not imply that billing stopped; record duplicate/canceled requests in usage metrics.

Thinking-pause tests are separate from latency on clearly finished speech. Do not tune endpointing to cut off normal learner planning just to meet the reply metric. If the selected turn detector cannot meet both criteria, adjust its endpointing/adapter and rerun the same audio set; do not change the interaction to mandatory push-to-talk.

| Failure | Required technical response |
| --- | --- |
| Microphone denied/missing | Do not connect as listening; explain access retry and offer expression exploration |
| LiveKit/agent unavailable | Timeout connection, release ownership, preserve session, offer reconnect |
| LiveKit Inference auth/quota/model error | Redacted actionable error; no direct-provider fallback, scripted answer, or fabricated score |
| Transcription unavailable | Keep a sealed input pending while RAM exists; retry that operation, or ask to repeat after evidence is lost |
| Invalid/failed turn proposal | Preserve accepted work; retry the same causal operation without double-counting |
| TTS or browser autoplay failure | Retain generated words; mark delivery failed and offer explicit replay/audio unlock |
| Redis unavailable | Stop accepting/acknowledging new answers; pause media because state cannot be safely saved |
| Assessment timeout/invalid output | Preserve exchange and valid feedback; show affected unavailable dimensions and retry from saved original wording |

## 10. Docker and configuration contract

### Compose topology

| Service | Packaging and role | Exposure / health |
| --- | --- | --- |
| `web` | Multi-stage Node 22 build of the frontend; Nginx serves static assets and proxies `/api` including SSE without buffering | Host `${APP_PORT}` → container 80; HTTP health path |
| `api` | Python backend image running FastAPI on 8000 | Compose network only; liveness and readiness that checks Redis and agent availability |
| `agent` | Same Python image, separate LiveKit agent-server command in non-development mode | Outbound connections to LiveKit Cloud/Inference; private SDK health endpoint, normally 8081 [L7] |
| `redis` | Pinned Redis 7.4 image, snapshots/AOF disabled, bounded memory with `noeviction` | Compose network only; `redis-cli ping`; no host port or persistent volume |

The agent registers with LiveKit Cloud; it is not deployed to LiveKit's agent-hosting platform for this release. The browser connects directly to the Cloud media endpoint while API/SSE traffic goes through the local web service. LiveKit Inference handles all remote model calls. Do not add a local LiveKit media server, a GPU service, a second Redis dependency, or imply that Compose starts external model infrastructure.

Read configuration from the root `.env` through Compose's explicit environment mapping. Inject only the values each service needs. Secrets never become Vite variables, build arguments, frontend assets, logs, or git content. Frontend API URLs are relative; the API returns the public LiveKit URL and a scoped token at connection time. All session/TTS HTTP responses disable caching; Redis is not a public service.

### Required `.env.example` contents at implementation

The following is the configuration contract, not a populated credential file. Empty secrets fail startup validation with their variable names, never their values.

```dotenv
APP_PORT=8080
APP_ORIGIN=http://localhost:8080
COOKIE_SECURE=false
GUEST_COOKIE_SECRET=
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
LIVEKIT_AGENT_NAME=workplace-english-tutor
CONVERSATION_MODEL=google/gemini-3.5-flash
TRANSCRIPTION_MODEL=deepgram/nova-3
TRANSCRIPTION_LANGUAGE=en
ASSESSMENT_MODEL=google/gemini-3.5-flash
TTS_MODEL=cartesia/sonic-3
TTS_VOICE=a167e0f3-df7e-4d52-a9c3-f949145efdab
REDIS_URL=redis://redis:6379/0
SESSION_TTL_SECONDS=86400
VOICE_LEASE_SECONDS=15
MAX_ACTIVE_SESSIONS=4
ASSESSMENT_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

Validate the retention setting so it cannot exceed 86,400 seconds. Product turn limits and rubric anchors are versioned domain rules, not environment knobs. Default privacy settings always disable recordings and payload logs; do not introduce an undocumented switch that retains learner audio.

The README must document generating a random guest-cookie secret, obtaining the LiveKit Cloud URL/key/secret, enabling sufficient Inference access/credit, and the startup command. No separate model-provider account/key belongs in the setup:

```sh
docker compose up --build
```

Health probes do not incur model calls. Agent availability means a fresh worker heartbeat after successful LiveKit registration and local initialization, not just an open health-check port. A separate documented preflight command in the backend image verifies STT, LLM conversation, wording assessment, and TTS through LiveKit Inference using non-personal fixture content. It identifies unsupported model/options and prints redacted results. Record that it makes billable test calls. A valid media connection alone does not prove Inference access.

Build dependencies and necessary local model assets into the image. Use lockfile-based installation, non-root application processes, `.dockerignore` entries for `.env`/`.git`/unrelated design artifacts, and no startup dependency installation. Configure a bounded shutdown grace period: fence new work, mark owned sessions paused, stop media, finish/cancel bounded result work, and free audio. API and agent restarts must not rely on local files for session restoration.

### Clean-checkout acceptance

A reviewer copies `.env.example` to `.env`, supplies only LiveKit external credentials and the generated cookie secret, and runs Compose without installing Python, Node, Redis, or the LiveKit CLI on the host. The app serves on the documented port and performs a real spoken conversation and real wording assessment. Run this check with every direct-provider API key absent. All remote model requests must target LiveKit Inference; an SDK's internal OpenAI-compatible HTTP client is acceptable and must not be confused with a direct OpenAI service dependency. Document optional phone HTTPS setup separately. Missing credentials produce a clear setup error, never a simulated connected experience.

## 11. Data handling and operational visibility

| Processor/store | Data sent or held | Policy for this implementation |
| --- | --- | --- |
| Browser | Live mic frames, transient playback, rendered transcript/results, guest cookie | No learner recording persistence; stop tracks explicitly; no session-content localStorage/IndexedDB cache |
| Agent RAM | Current-answer audio, streaming transcript, model context, in-flight text assessment | Bounded lifetime from section 7; release accepted audio and clear obsolete SDK contexts |
| Redis | Session text, scores, evidence descriptions, timestamps, access/ordering state | Activity-based expiry ≤ 24 hours; no disk persistence in take-home configuration |
| LiveKit Cloud | Live media transport and connection metadata | No Egress; `AgentSession.start(record=False)` to disable audio/transcript/trace/log collection for each session; document Cloud project setting too [L11] |
| LiveKit Inference STT | Learner audio for transcription | LiveKit's documented zero-data-retention policy for Inference, including its underlying providers [L2] |
| LiveKit Inference LLM | Transcript/context for conversation, wording assessment, and targeted retry feedback | Same Inference policy; no learner audio supplied to the LLM [L2] |
| LiveKit Inference TTS | Approved tutor/coaching/example text | Same Inference policy; stock voice, no voice-cloning uploads [L2] |

LiveKit documents zero data retention by default for all Inference LLM/STT/TTS models and plans: prompts, audio, and outputs are not stored, logged, or used for training by LiveKit or its underlying inference providers. This applies to Inference traffic, not the application's Redis records or separately enabled Agent Insights. Document the actual route and recheck the policy at release. [L2]

LiveKit's current observability documentation says collection may include local recordings uploaded after the session and a 30-day Cloud retention window. Explicitly passing `record=False` is necessary; merely avoiding an Egress call is insufficient. Verify the SDK produces no local recording or session-report files and uploads no content telemetry with the chosen configuration. Do not copy tutorial transcript-printing examples into application logs. [L11, L12]

Before microphone use, show a short disclosure that speech is processed through LiveKit and its model providers, application history is temporary, and the tutor voice is AI-generated. Link to a concise provider/data explanation and identify the selected STT/LLM/TTS providers there. Delete removes application-held session content and stops live work; it does not claim to operate external providers' deletion systems.

Log only operation IDs, phase, error category, timing, numeric usage, and counters. Never log raw prompts, transcripts, tool arguments containing speech, base64, provider tokens, cookie values, or full session reports. Redact SDK/HTTP exception bodies. Retain no user-content analytics in the take-home. Track active jobs, model errors, timeouts, lease loss, rejected stale writes, and assessment availability to diagnose behavior.

## 12. Verification and release gates

### First integration gate

Before building all screens, demonstrate one real purpose through the selected stack using LiveKit credentials alone: generated opening → two spoken learner answers → controlled coaching transition → two wording-supported dimensions → Finish → refresh and Review. Also demonstrate a pause during an answer, a barge-in, and the capped-answer submit/retry choices. This is an implementation acceptance gate, not a claim that the prototype already exists.

Verify the exact pinned SDK's STT finalization, turn detector, application-controlled response generation, Inference text/TTS combination, audio boundaries, interruption flushing, and recording opt-out. If an API mapping is unsupported, resolve it in the adapter and update this specification. Do not silently switch to a direct-provider API, bypass LiveKit browser transport, or use prepared successful conversations.

### Test layers

| Layer | What it establishes |
| --- | --- |
| Domain tests with a controllable clock and real Redis integration cases | Atomic state transitions, 2/3 and 1/2 budgets, 60/120-second behavior, continuation budgets, idempotent input/commands, expiry, deletion races, ownership, stale-result rejection |
| Inference-contract tests | LiveKit-only authentication; valid/invalid result schemas; transcript-ID mapping and quote provenance; no audio dimensions/bases; deadlines and error mapping |
| LiveKit text debugger / agent tests | Answer-dependent reasoning, phase context, goal judgment, coaching questions, help classification, and supported tool behavior; these do not prove audio quality |
| Real audio integration checks | End detection, barge-in, physical-device playback/capture, TTS delivery, transcript fidelity, and recovery boundaries |
| Browser tests | Portrait bounds, navigation, controls, event reordering, local media stops, completed review without capture, and session isolation |
| Clean Compose smoke test | Host-independent startup, actual providers, Redis-backed recovery, redacted failure messages, and no recording files |

### Representative audio set

Create at least 24 short exchange fixtures across the nine purposes, including at least eight human-recorded examples from consenting speakers with varied accents. Human audio checks STT fidelity and turn handling; text fixtures check wording feedback. These are explicit test assets with provenance, not retained learner sessions or a pronunciation benchmark.

Cover clear short answers, longer multi-sentence answers, ordinary 1–3-second thinking pauses, filler/restarts, a deliberately unfinished clause, a completed concise answer, silence, background noise, isolated acknowledgments, varied accents, recognition ambiguity, identical wording spoken with different intonation, tutor leakage, mid-answer Pause, barge-in, and continuation after premature endpointing. When the recognized wording/context is identical, intonation must not cause different assessment claims; it is outside the assessor's input.

For turn-taking, run at least ten pause/continuation cases and ten finished-answer/manual-submit cases. Require no double counts, no substantive response during designated ordinary thinking pauses in at least 9/10 cases, and reliable single submission with **I'm done** in all manual-submit cases. Run at least ten intentional interruptions: no obsolete utterance may resume. Verify first-speech timing, one 60-second visual cue, capture stop at 120 seconds, explicit submit/retry, cap/end-event races, same-answer continuation budgets, and loss of a capped candidate on recovery. Duration must not award or deduct points. Measure latency separately.

For assessment, two human reviewers familiar with the rubric annotate wording sufficiency and defensible score ranges before seeing model results. Require eligible full-evidence fixtures to exercise both dimensions; silence/acknowledgment-only fixtures to avoid a fabricated full scorecard; uncertain transcription to be treated cautiously; every evidence reference/quote to resolve; and no delivery or invented quotation claims. At least 80% of supported dimension judgments should fall within the agreed range, with larger disagreements reviewed and addressed. These are formative-feedback acceptance checks, not validated proficiency measurement.

Repeat a representative six-exchange subset three times to inspect instability in availability and score judgments. Fix prompts/model choices when results are inconsistent or depend on unprovided delivery cues. Check STT recognition across accents. For tutor voice delivery, human reviewers listen to real generated roleplay, coaching, and modeled expressions across all purposes; reject rushed, monotonous, mis-stressed, or context-inappropriate examples. Prepared mockup clips cannot satisfy this check.

### Product acceptance mapping

| Product scenario | Verification |
| --- | --- |
| A01 | Browser geometry, readable text, keyboard focus, and ≥44×44 targets at reference/smaller/desktop sizes |
| A02 | Content schema checks for nine purposes, ordered scenarios, audible expressions, and correct practice entry |
| A03 | Live audio conversations: generated opening plus follow-ups that use actual learner details; count learner answers only |
| A04 | Two-answer goal-achieved case closes with acknowledgment/bridge and no outstanding question |
| A05 | Three-answer goal-not-demonstrated case cannot produce a fourth roleplay prompt |
| A06 | Representative pause audio, manual submission, 60/120-second cue/cap, continuation timing, and cap-choice races; one accepted input |
| A07 | Real barge-in and same-answer continuation; obsolete playback canceled and count remains correct |
| A08 | Control matrix tests, including helpers during Pause and no helper audio in evidence |
| A09 | Reliable-wording fixtures exercise two separate 1–5 scores and transcript evidence; no aggregate/audio dimensions |
| A10 | Insufficient/unclear transcripts produce dimension-specific availability reasons |
| A11 | Retry ends after one or two answers; feedback cites new evidence; original scores unchanged |
| A12 | Finish with zero/one accepted answers and during capture; no fabricated completion or partial-answer score |
| A13 | Refresh/network loss at each pending-work boundary; snapshot restore paused; no automatic capture or duplicate answer |
| A14 | Provider timeout/auth/quota, TTS failure, autoplay denial, and invalid assessment injections |
| A15 | Controlled-clock expiry and Delete/result races; list/review/heartbeats do not extend retention |
| A16 | Fresh checkout/root `.env`/Compose demonstration with only LiveKit external credentials plus assignment packaging checklist |
| A17 | Resume roleplay, coaching, and retry with exact saved situation/prompt/count |
| A18 | Review without mic; Practice again uses distinct session/opening and fresh evidence while preserving prior results |
| A19 | Two tabs and two sessions competing for ownership; old room fenced before new capture is authorized |
| A20 | Physical-device listening review of natural rhythm, intonation, role-appropriate tone, and modeled delivery |
| A21 | A fixture with different issues in early and late answers produces both useful notes and one retry priority |

Release gates additionally include a worker restart while Redis survives and pending wording assessment resumes, Redis loss with honest unavailable history, and log/filesystem inspection for accidental learner recording/transcript copies. Mocks establish deterministic mechanics; actual Inference calls and audio runs establish wording assessment and voice behavior respectively.

## 13. Submission and scaling

The implementation must include the assignment verbatim in `PROMPT.md` (verify against the source, not a paraphrase), startup/architecture/tradeoffs in `README.md`, a truthful `workflow.md` identifying tools and model choices actually used, `.env.example`, and a real demonstration video. Package source and `.git` in the submission zip, excluding secrets, dependency caches, and non-consensual recordings. Use explicit demonstration input for the video. This specification does not claim those deliverables already exist.

The README's 10,000-concurrent-session discussion should cover:

- Scale stateless API instances separately from long-lived agent jobs; use managed LiveKit media, warm agent capacity, measured per-job resource usage, and graceful draining. A request-per-second estimate is not an agent concurrency estimate.
- Use shared Redis with high availability, sharding by guest, atomic ownership, capacity planning, and a documented persistence/deletion strategy. Browser recovery and storage disaster recovery remain different guarantees.
- Obtain sufficient realtime connection and model quotas; separately budget transcription, TTS, and bursty end-of-exchange assessments. Apply admission control instead of accepting sessions that cannot receive timely speech.
- Run wording assessment from saved immutable transcript snapshots so it can move across workers. Any future durable queue contains bounded job references and must honor session expiry/deletion; it does not need learner recordings.
- Bound current-answer PCM memory: at an 8 MiB application-buffer budget, 10,000 simultaneously full buffers alone approach 78 GiB before SDK/model context and process overhead. Measure actual occupancy, release accepted audio promptly, and distribute jobs accordingly.
- Measure regional RTT, p95 speech latency, assessment availability, costs, and active jobs; scale down only after draining. Keep content-free metrics and evaluate voice quality after provider/model changes.

The first release implements neither a distributed job-queue system nor Kubernetes. Its module boundaries, explicit state ownership, and acceptance checks preserve a path to those changes without adding them to the take-home.

## 14. Sources checked for this draft

Official documentation was consulted on 2026-09-26. Documentation establishes the cited capabilities; it does not replace checking the installed SDK, available model access, or measured behavior.

| Reference | Source and use |
| --- | --- |
| L1 | [LiveKit pipeline types](https://docs.livekit.io/agents/models/pipelines.md): half-cascade, direct realtime, and transcription-pipeline tradeoffs |
| L2 | [LiveKit Inference](https://docs.livekit.io/agents/models/inference.md): model catalog, consolidated access/billing, and zero data retention |
| L3 | [LiveKit turns and interruptions](https://docs.livekit.io/agents/logic/turns.md): manual controls, input clearing, and false-interruption behavior |
| L4 | [LiveKit nodes and hooks](https://docs.livekit.io/agents/logic/nodes.md): restrictions on the realtime user-turn-completed hook |
| L5 | [LiveKit raw media tracks](https://docs.livekit.io/transport/media/raw-tracks.md): learner-track PCM frame access |
| L6 | [LiveKit explicit dispatch](https://docs.livekit.io/agents/server/agent-dispatch.md): named agent jobs and metadata |
| L7 | [LiveKit self-hosted agent deployment](https://docs.livekit.io/deploy/custom/deployments.md): Docker, outbound registration, and health endpoint |
| L8 | [LiveKit Cartesia TTS](https://docs.livekit.io/agents/models/tts/cartesia.md): Inference model/voice catalog and supported delivery controls |
| L9 | [LiveKit sessions](https://docs.livekit.io/agents/logic/sessions.md) and [events](https://docs.livekit.io/reference/agents/events.md): lifecycle, transcripts, speculative generation, and errors |
| L10 | [LiveKit tokens and grants](https://docs.livekit.io/frontends/reference/tokens-grants.md): room permissions, reconnect expiry, and revocation |
| L11 | [LiveKit Agent Insights](https://docs.livekit.io/testing/observability/insights.md): recording defaults, `record=False`, and Cloud observability retention |
| L12 | [LiveKit data hooks](https://docs.livekit.io/testing/observability/data.md): session reports and content telemetry |
| L13 | [LiveKit LLM overview](https://docs.livekit.io/agents/models/llm.md) and [Gemini Inference](https://docs.livekit.io/agents/models/llm/gemini.md): standalone requests, model catalog, and options |
| L14 | [LiveKit Deepgram STT](https://docs.livekit.io/agents/models/stt/deepgram.md): Nova-3 through Inference, language and transcription controls |
| L15 | [LiveKit turn detector](https://docs.livekit.io/agents/logic/turns/turn-detector.md): text detector, STT/VAD requirements, and local execution |
| L16 | LiveKit Agents source inspected on 2026-09-26: [Inference LLM serialization](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/inference/llm.py) and [OpenAI-compatible context conversion](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/llm/_provider_format/openai.py). The standard path skips audio content; this is not a claim about every possible gateway/custom API. Recheck against the pinned implementation version. |
