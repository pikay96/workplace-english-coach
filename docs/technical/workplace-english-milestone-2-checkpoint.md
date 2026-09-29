# Milestone 2 checkpoint

Date: 2026-09-26. Status: **milestone 2 implemented; integration checkpoint verified**. Work stops here. Milestones 3–5 remain outside this checkpoint.

Historical checkpoint: subsequent user authorization extended implementation through milestone 4. See the [current checkpoint](workplace-english-milestone-4-checkpoint.md) for current features and verification. The evidence and failures below describe the earlier implementation.

The implementation follows the [approved implementation plan](workplace-english-implementation-plan.md). Welcome everyone is the only enabled purpose. The existing portrait mockup supplies the visual direction and licensed assets; runtime conversations and scores come from live Inference.

## Implemented scope

- Four Compose services, pinned SDK/tool versions, lockfiles, approved package mirrors, cached local detector assets, validated configuration, and non-model health checks.
- Guest-scoped Redis transactions, session/command/evidence schemas, idempotent submission, two/three-answer budgets, staged ownership, absolute expiry, and deletion fences.
- Application-controlled LiveKit turn completion, approved words saved before speech, automatic/manual sealing, a RAM-only current-answer buffer, a 60-second cue, and explicit 120-second cap choices.
- Separate original-exchange assessment with exactly two wording dimensions and validated answer IDs, revisions, and exact transcript quotes.
- Portrait React UI with disclosure, Start, Pause, Resume, Finish, saved words, temporary recent sessions, and completed Review with optional HTTP speech.

## Turn-taking correction after the checkpoint

On 2026-09-26, the user clarified that Alex must finish speaking before listening.
This supersedes the speech-interruption behavior recorded in the original
checkpoint below. It does not expand implementation into milestone 3.

- Browser microphone publication and server capture stay disabled during Alex's
  output, including gaps between TTS chunks. Speech-start events cannot cancel
  output. SDK speech interruption is disabled and overlapping audio is discarded.
- Successful, still-authorized playback opens a fresh answer input. Its clock
  starts on subsequent learner speech. Failed playback and stale completion
  after Pause cannot enable capture. Pause and Finish still cancel output.
- The UI explains that the microphone is off while Alex speaks; **I'm done** is
  available during the learner's turn. Product and technical requirements now
  describe alternating turns.
- Regression verification: **32 backend tests**, **6 frontend tests**, and **2
  ordinary browser checks** passed; Ruff and production builds passed.
- The focused real WebRTC test passed in **2.4 minutes**: speaking during Alex's
  output left playback active and input absent; Pause stopped audio; Resume played
  the saved opening before capture; mid-answer Pause discarded unsent input; the
  next resumed answer was manually submitted exactly once and its follow-up played.
- The first broader live journey saved two answers and generated assessment but
  exceeded the test's combined 100-second bridge/assessment/coaching wait while
  coaching was still playing. The correctness-test wait now accounts for two
  separately bounded speech operations. Application deadlines are unchanged;
  this adjustment does not claim improved latency.
- The rerun completed generated opening, two real answers, spoken follow-up,
  bridge and coaching, Finish, reload, and unchanged saved assessment. Optional
  HTTP Review speech then produced no audible frames; the API recorded a
  `TimeoutError` in that synthesis operation. The full test therefore **failed**
  at Review audio and is not counted as a complete gate pass. The focused
  alternating-turn test above passed independently; the delivery issue remains.

The [audio-delivery diagnosis](workplace-english-audio-diagnosis.md) remains open:
turn-taking prevents speech-triggered cancellation but does not repair incoming
TTS chunk delays. Physical-speaker testing remains outstanding.

## Original checkpoint verification evidence

| Check | Observed result |
| --- | --- |
| Compose build and readiness | All four services built and became healthy. Web health check uses IPv4 explicitly. |
| Backend tests with real Redis | 24 passed, including successful paths, duplicate acceptance, three-answer limit, ownership revocation, expiry/delete, guest isolation, evidence checks, Pause during STT finalization, queued-output fencing, manual SDK finalization, flush silence, interim-tail uncertainty, and delayed interruption callbacks. |
| Frontend unit tests | 5 passed: revision-conflict intent preservation, connection fencing, microphone readiness ordering, and Review cancellation during request/streaming. |
| Frontend production build | Passed. The LiveKit bundle produces a size warning; initial bundle optimization is not claimed. |
| Ordinary browser checks | Portrait/disclosure and completed Review without microphone tests passed at 390×844, 320×640, and 1440×1000. |
| Live provider preflight | Conversation, TTS, streaming STT finalization, and evidence-validated assessment all passed using LiveKit credentials only. |
| Actual browser WebRTC | The complete two-answer gate passed on the revised voice adapter: generated opening, two spoken answers, acknowledgment/bridge, spoken coaching, two evidence-supported scores, Finish, refresh, unchanged saved results, and HTTP Review speech without a microphone or room. Every completed tutor message's played text matched its approved saved text. |
| Interruption/Pause/manual submit | Passed with real browser audio: interrupt the opening, observe silence without obsolete resumption, Pause during the unsent answer, Resume, and submit one answer with I'm done. |
| Three-answer closure | Passed with real spoken answers: two incomplete welcome attempts receive follow-ups, the third closes the exchange, and no fourth input is opened. |
| Actual 60/120-second boundaries | Passed in 4.8 minutes: the cue appears, both candidates reach 120 seconds without automatic acceptance, Try again creates a fresh input under the same question, and Use this answer accepts exactly one capped answer. |

The final live run covering the core journey, interruption/Pause/manual submission, and both cap choices passed all three tests in 10.5 minutes. The three-answer branch passed in its preceding focused run. These results preserve earlier failed attempts as diagnostics, not successful measurements. The final Review-cancellation and Finish-notice copy fixes were checked with unit/state tests and a production build after the live run.

## Compatibility findings

LiveKit Agents 1.8.2 rejects a dictionary passed through its `response_format` parameter. The adapter uses the supported `extra_kwargs` path and a portable JSON-schema envelope. Provider-only schema simplification does not remove Pydantic bounds or application evidence validation. Assessment context includes original evidence and its prompts, excluding transport/input/generation identifiers.

The streaming STT preflight must stop at a final transcript event instead of waiting for iterator exhaustion after ending input. The agent itself uses the SDK's manual `commit_user_turn(..., skip_reply=True)` and raises `StopResponse` from the automatic completed-turn hook.

In SDK 1.8.2, `commit_user_turn` returns the transcript before its end-of-turn task completes. That task can still interrupt background `say()` handles. The adapter waits for the current activity's `wait_for_idle(wait_for_user=False)` within the same bounded finalization operation before opening another input or scheduling its reply. Access through `current_agent._get_activity_or_raise()` is a pinned SDK compatibility seam: session-level idle also waits for a VAD silence event that may remain latched after capture is disabled. Regression coverage checks the task boundary and excludes that disabled-capture wait.

Manual/cap finalization permits the SDK's silent flush frames through STT after microphone input is disabled, without appending them to the sealed PCM buffer or allowing more speech. Submitted text that contains an unfinalized interim tail is marked unclear; it cannot support a score as reliable wording.

Approved `say()` output uses application-owned interruption. Current-input speech-start events can force cancellation, while the SDK's automatic cancellation from late STT is disabled for that output. Capture remains enabled during playback. A callback retains the original output handle across its state write, so it cannot cancel a newer reply.

Both local detector runners are registered by the pinned plugin, so both sets of assets are cached during the build. Runtime Hugging Face access is disabled. The coordinator uses the public worker-registration event plus the pinned SDK's connection-state flags; broader restart recovery is milestone 3 work.

Recording is disabled at job entry and session start, including audio, transcripts, logs, and traces. Session hosting is disabled. Application logs contain allowlisted metadata only. The Windows fixture harness generates non-personal speech in memory with System.Speech and feeds it through browser WebRTC; it does not record a learner. Actual STT, conversation, assessment, and tutor TTS use LiveKit Inference.

## Issues found during validation

- Fixed microphone initialization ordering, stop-command revision reconciliation, queued-speech generation fencing, and chronological reconstruction of heard/accepted detector context.
- Fixed nginx retaining a removed API container's address after a rebuild by using Docker DNS resolution for its upstream. This affected the test setup before a session could start.
- An assessment result was rejected on a repeat live run. The app retained the accepted answers and exposed Retry. The assessment prompt/context was made more specific, and two focused fixture rechecks passed; this is not a statistical quality guarantee.
- A repeated intelligible but off-goal answer was treated as a help request. The prompt now distinguishes an answer attempt from an actual request for help, preserving the three-answer budget.
- An inconsistent turn proposal failed both initial and repair validation. The model context now supplies the prospective answer number and explicit permitted action combinations; application validation still rejects incompatible decisions.
- Standalone TTS diagnostics started audio in about 3 seconds but took approximately 48–49 seconds to finalize about 11 seconds of audio. The adapter now separates the eight-second first-frame deadline from a bounded 90-second full playback deadline. Automatic SDK TTS retries are disabled so partial audio is not repeated. This delay is a material performance limitation pending further measurements.
- Test-harness selector and transient-state mistakes were corrected. Failed runs are not counted as complete integration-gate passes.
- A repeat of the core journey produced valid saved coaching but its bridge speech exceeded the eight-second first-frame deadline. The app retained the words and marked that delivery failed. The earlier complete core pass does not establish consistently successful provider latency.
- Inspecting the actual Review screenshot exposed a spurious failure notice after Stop audio. Explicit cancellation now settles quietly, with request/stream regression tests. Finish also distinguishes saved progress from actual discarded speech.

Two completed live two-answer runs produced these observations:

| Run | Page entry → first opening audio | Page entry → completed opening | Entire tested journey |
| --- | ---: | ---: | ---: |
| Initial complete gate | 22,198 ms | 58,161 ms | 170,613 ms |
| Revised voice adapter | 19,879 ms | 54,723 ms | 207,876 ms |

The full journey includes fixture answers, playback completion, Review reload/playback, and assertions. These are individual end-to-end observations, not p50/p95 benchmarks or passed release latency targets. The portrait home and actual saved Review were visually inspected; the latter inspection led to the cancellation-notice fix above.

Browser checks used installed Microsoft Edge 153.0.4234.32 on Windows. Docker Engine was 29.8.0. These are desktop fixture checks, not physical-phone or microphone evidence.

## Handoff and remaining limits

Run the four services with the commands in [README.md](../../README.md), then open `http://localhost:8080`. Welcome everyone is the only enabled purpose. The checkpoint demonstrates the real integration path and bounded error handling; it does not establish release readiness.

TTS latency and occasional provider deadline failures remain material limitations. Human listening, physical microphone/echo behavior, subjective coaching quality, repeated latency benchmarks, multi-tab/restart recovery, focused retries, and all-purpose UI are not established by these automated fixture checks. Continue with milestone 3 only after reviewing this checkpoint; no milestone 5 packaging or release claim is included.
