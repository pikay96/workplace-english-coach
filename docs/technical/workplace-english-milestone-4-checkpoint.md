# Milestone 4 checkpoint

Date: 2026-09-26. Scope: **implementation through milestone 4, stopping before milestone 5**, as subsequently authorized by the user. All nine purposes and the practice → coaching → focused retry → saved Review journey are implemented. This is an implementation checkpoint with the limitations below, not a release-readiness claim.

Subsequent scope update, September 27: the user approved a feature freeze and the submission essentials plus a desktop rehearsal. See [demo verification](../verification/workplace-english-release-checks.md) for that work; the broader evaluation below remains deferred. This document preserves the earlier milestone 4 evidence.

The [implementation plan](workplace-english-implementation-plan.md) defines scope. The [milestone 2 checkpoint](workplace-english-milestone-2-checkpoint.md) preserves earlier evidence and failures. Run the application using [README.md](../../README.md), then open `http://localhost:8080`.

## Implemented after milestone 2

- All nine purposes in the required Hosting a meeting → One-on-one → Casual talk order, with expressions, alternatives, examples, goals, roles, hint starters, and bounded situation variations. Purpose-specific opening directions keep Alex in the colleague role and the communication goal with the learner.
- Same-answer continuation with one logical answer ID, incremented revisions, merged wording/duration, and superseded obsolete follow-ups. **I wasn’t finished** starts an explicitly bounded continuation interval during the learner's turn. The cue includes the earlier answer's duration; tutor playback does not consume its allowance.
- Mute/Unmute, Hear Alex, Hint, expression playback, and cap discard rules. Explicit Mute stops the underlying microphone track immediately and preserves tutor output. The managed LiveKit track is reacquired on an authorized Unmute. Unmute during replay opens capture only after replay completes.
- Alex always finishes speaking before listening. Capture is disabled during generation and playback, including gaps between audio chunks. Speech cannot cancel Alex. Pause, Finish, replay, and navigation remain explicit controls over output.
- Hint pauses practice, discards unsent input, saves a separate helper intent, and may play that helper once through HTTP. Helper playback cannot resume roleplay or become learner evidence. Resume explicitly returns to the saved phase/prompt.
- Atomic default four-session admission, room reservations and expiry cleanup, foreground heartbeats, BroadcastChannel/Web Locks coordination, and server connection-epoch fencing. Failed/late dispatch, Delete, lost leases, and released owners cannot silently keep an authorized publisher.
- Lost-owner sessions recover paused. Unsaved or capped RAM input is discarded with an honest repeat notice; accepted answers and saved tutor words survive API/agent restarts when Redis survives.
- A bounded agent-service coordinator scans canonical session records with a persistent cursor, claims original/retry assessments, expires failed attempts, cancels deleted/obsolete work, and conditionally commits results. Pending frozen assessment can complete without a room, microphone, Resume, autoplay, or retention renewal.
- Spoken coaching questions use separate records. Focused retries use separate IDs, a one-to-two-answer limit, their own frozen evidence and targeted assessment. Retry feedback cannot change original scores or automatically claim improvement.
- Early Finish, including zero-answer expression reminders and one-answer assessment; Recent sessions; phase-aware Resume; completed Review; Delete; and Practice again with fresh evidence and a bounded duplicate-opening retry.
- One frontend media owner for LiveKit and HTTP expression/Hint/Review speech. HTTP streams use four-byte big-endian PCM lengths, a zero completion marker, and `0xffffffff` for failure. An incomplete stream is unavailable, not successful playback. No personalized audio cache or saved learner recording was added.
- Portrait scenario navigation, expression exploration, practice controls, coaching evidence/notes, focused retry feedback, and return flows using the existing ivory/sage, Newsreader/Jakarta design.

## Verification observed

| Check | Result and limit |
| --- | --- |
| Backend suite with real Redis | **54 passed**. Covers answer/command deduplication, budgets, continuation revisions, total-duration cue/cap, separate retry evidence, score immutability, late Hint/results, admission races, old-owner fencing, loss/recovery, and audio adapter ordering. |
| Backend style | Ruff check passed; formatter discrepancy in the opening-normalization helper was corrected. |
| Frontend unit suite | **7 passed**, including canonical capture permission and HTTP playback cancellation/framing. |
| OpenAPI and build | OpenAPI exported, TypeScript API types regenerated, production frontend and Compose builds passed. Vite retains its large-bundle warning (about 812 kB uncompressed JavaScript); bundle optimization is not claimed. |
| Portrait/browser fixtures | **3 passed**: disclosure/no-mic entry and geometry, completed Review without microphone/room, and all-nine navigation. Viewports: 390×844, 320×640, 360×740, 1440×1000. Tested home buttons, summaries, and disclosure hit area at ≥44×44, keyboard scenario navigation/focus, and scroll reachability. Home and empty Review screenshots were visually inspected. These are desktop browser fixtures, not physical phone checks. |
| Nine-purpose actual model fixture | `check_learning.py` completed generated openings and accepted exchanges for all nine purposes using actual Inference. Eight closed at two answers; Follow-up closed at three. These are synthetic text inputs, not nine physical audio journeys or human quality ratings. |
| Full live coaching/retry journey | **Passed in 7.6 minutes**: generated opening → two spoken answers → spoken coaching → coaching question/reply → focused retry → targeted spoken feedback → Finish → reload without microphone → Practice again with a different opening. Original answers and original assessment stayed unchanged, and retry evidence referenced retry answers only. |
| Live controls and two tabs | **Passed in 3.9 minutes**: spoken answer → explicit continuation under the same ID/revision 2 → Mute with ended microphone track → saved-word replay → Unmute → paused Hint → Resume → second-tab takeover with new epoch and ended old microphone track → Finish. |
| Actual HTTP expression speech | **Passed in 10.7 seconds**: audible framed PCM, Stop audio stops playback, and zero microphone requests. This does not establish reliable latency or every saved-Review audio path. |
| Actual API/agent restart | Passed `check_restarts.py`: API preserved session/expiry; agent recovered a frozen pending assessment, discarded lost capped input, preserved the prompt, and completed assessment without Resume/autoplay. |
| Actual Redis process loss | Passed `check_redis_loss.py` against disposable Redis on port 6380: old session became unavailable, Recent was empty, and no session was resurrected. The application's Redis/history was not erased. |
| Running application | All four Compose services healthy; `/health/ready` returned `{"status":"ready"}` after the final build. |

The live browser harness uses installed Microsoft Edge 153 on Windows. Non-personal learner fixture speech is generated with System.Speech in RAM, sent over browser WebRTC, and processed by the actual product STT/conversation/assessment/TTS routes. The stack remains LiveKit Agents/plugins 1.8.2, livekit-api 1.2.1, browser client 2.22.3, Python 3.12, and Node 22. No mocked provider replies or scores satisfy the live checks.

Earlier milestone 2 evidence includes a successful real three-answer closure, both real 120-second cap choices, and a focused alternating-turn test that injected speech during Alex's output and verified it did not interrupt. Those runs are historical evidence; they were not all repeated after the milestone 4 changes. The relevant adapter regressions passed in the current suite.

## Failures found and corrected

- Some generated openings reversed the learner/tutor role or addressed the learner as Alex. Added per-purpose opening direction and explicit role/name instructions, then reran all nine model exchanges. Their subjective naturalness still requires human review.
- A live explicit continuation returned `new_answer`, failing domain validation. Explicit continuation now uses a constrained response relation and the unchanged prospective answer count. A regression verifies one answer at revision 2.
- Unmute during replay could be lost because playback captured the old restore-input flag. Completion now reads the latest permission. A regression holds playback open, unmutes, and verifies capture stays closed until delivery completes.
- Continuation's 60-second cue originally counted only the current fragment. A failing adapter regression reproduced this; the cue now includes previously consumed allowance while the cap remains tied to the remaining duration.
- The first two-tab browser assertion read only `MediaStreamTrack.enabled`. That property can remain true on an ended track. The harness now checks both enabled and live state, and the successful rerun explicitly asserts that the old track ended.
- The expanded portrait check found a 35-pixel disclosure hit area. Its minimum height is now 44 pixels; the four-viewport and keyboard check passed after the fix.
- Earlier live attempts encountered provider deadlines and strict model-output rejection. Those failures are retained in the prior checkpoint and are not counted as passes. A failed local UI run also used an empty `TEST_APP_URL`; unsetting the variable restored the intended Vite test URL.

## Remaining limitations and milestone 5 boundary

**Audio continuity update, September 27:** complete replies are now buffered before live and HTTP playback. The original starvation diagnostic passed with zero application delivery gaps, and a real browser opening had a longest measured quiet gap of 100 ms. The upstream network/gateway/provider bottleneck remains unidentified; buffering avoids its mid-reply stalls by adding preparation time. See the [audio diagnosis](workplace-english-audio-diagnosis.md). These observations do not establish release latency targets or physical-device performance.

**Inferred continuation has a capture-timing limitation.** Explicit **I wasn’t finished** enforces the remaining capture allowance from the start. An ordinary interval may instead be classified as continuation only after capture; the combined accepted duration is limited to 120 seconds, but that interval can capture beyond the earlier answer's remaining allowance before rejection. Accepted prior evidence is preserved. Automatic early classification/capture stopping is not established by this checkpoint and needs resolution before claiming full continuation acceptance.

Milestone 5 remains unimplemented: the representative 24-exchange evaluation set (including consenting human recordings), two blind rubric reviewers, repeated score/turn-taking calibration, physical Android/iOS/desktop microphone tests, at least 30 reply latency measurements, fresh-checkout release verification, exact-source `PROMPT.md`, walkthrough video, and inspected submission package. Physical speaker/echo behavior, speech quality across all purposes, and release latency/cost targets remain unverified. No release or submission-ready claim is made.

## Repeat the checks

Use the approved package feeds configured in the manifests. Follow README for a disposable Redis instance and local dependencies. In PowerShell:

```powershell
# backend/
.venv-m2/Scripts/python.exe -m pytest -q
.venv-m2/Scripts/python.exe -m ruff check .
.venv-m2/Scripts/python.exe export_openapi.py

# frontend/
npm run types:api
npm test
npm run build
$env:TEST_APP_URL='http://localhost:8080'
npm run test:browser -- portrait.spec.ts
$env:LIVE_VOICE_TEST='1'
npm run test:browser -- live-voice.spec.ts -g 'Hint, replay, mute'
npm run test:browser -- live-voice.spec.ts -g 'coaching question and focused retry'
npm run test:browser -- live-voice.spec.ts -g 'real framed HTTP'

# repository root; billable actual model checks
Get-Content backend/tests/live/check_learning.py |
  docker compose run --rm -T --no-deps api python -

# Do not restart services while a live browser check or user practice is running.
backend/.venv-m2/Scripts/python.exe backend/tests/live/check_restarts.py

# backend/; restarts only workplace-english-test-redis
.venv-m2/Scripts/python.exe -m tests.live.check_redis_loss
```

The virtualenv path above is this workspace's existing environment; a clean machine can use the README's `uv sync --locked` and `uv run` equivalents. Live checks make billable calls. The final application remains running. The disposable test Redis was removed after verification; application Redis and its temporary history were preserved.
