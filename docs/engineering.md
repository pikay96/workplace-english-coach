# Engineering notes

Workplace English Coach combines live audio with an application-owned session model. The learner should be able to finish an answer, receive feedback grounded in that answer, and return to accepted work after a connection failure.

The [README](../README.md#how-it-works) gives the architecture overview. These notes explain the implementation choices, their costs, and what would need to change at a larger scale.

## Code map

| Area                | Where to look                                                                  | Responsibility                                                                      |
| ------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Browser interface   | [Frontend app](../frontend/src/app/) and [features](../frontend/src/features/) | Present practice, controls, coaching, and recent sessions.                          |
| Browser audio       | [Voice controller](../frontend/src/voice/)                                     | Coordinate live audio, playback, and microphone access.                             |
| HTTP API            | [API](../backend/app/api/)                                                     | Establish guest identity, accept commands, stream state, and dispatch rooms.        |
| Session rules       | [Sessions](../backend/app/sessions/)                                           | Validate transitions, maintain ownership, recover work, and persist state.          |
| Conversation        | [Conversation](../backend/app/conversation/)                                   | Build prompts and context for openings, replies, hints, and coaching.               |
| Assessment          | [Assessment](../backend/app/assessment/)                                       | Request feedback, validate evidence, and coordinate pending assessments.            |
| Voice and providers | [Voice integration](../backend/app/voice/)                                     | Run the LiveKit agent, connect to inference, buffer speech, and serve replay audio. |
| Curriculum          | [Scenario content](../content/workplace-english.json)                          | Define the nine communication purposes, situations, and expression examples.        |

## Follow one exchange

1. The browser selects a purpose and creates a session through the API. A signed guest cookie identifies the browser.
2. The API arranges a LiveKit room and agent dispatch. The browser joins for live audio and receives saved application state over HTTP/SSE.
3. The agent generates an opening. During a learner answer, speech activity detection and transcription help capture the turn; application rules decide whether to accept it.
4. An accepted answer becomes part of the saved conversation. The model proposes a follow-up or a transition to coaching, and code validates that proposal.
5. A separate assessment request evaluates the saved exchange. Evidence checks verify supporting quotes against accepted answers before feedback is saved.
6. The learner can hear coaching, try a focused retry, or reopen the saved review later. A completed review uses saved feedback and does not request microphone access.

## Decisions and tradeoffs

- **Use a transcript-based voice pipeline.** The live path is learner audio → transcription → Gemini response → Cartesia speech. Having the words available makes validation, replay, and feedback easier to inspect, at the cost of separate transcription and synthesis steps. LiveKit Cloud handles media transport while the application services run locally in Docker.
- **Let code control the session.** The model proposes replies and coaching. Code validates them, counts accepted answers, and controls transitions. Saved command IDs and ownership checks prevent repeated actions and stale tabs from changing a session. The API and agent share these rules rather than maintaining competing versions of the state.
- **Assess wording only.** Naturalness and Workplace tone use transcripts, with quotes checked against accepted answers. A separate assessment request gives coaching its own rubric and context, but adds a model call. This version doesn't assess pronunciation, fluency, or vocal delivery.
- **Take turns speaking.** Alex finishes before the microphone opens for the learner. This makes the active speaker clear, but prevents spoken interruption. Pause and Finish can stop playback; Pause discards an unsent answer.
- **Prepare the full reply before playback.** Complete-reply buffering prevents gaps between incoming TTS chunks from reaching playback, but makes the learner wait longer before Alex starts. It doesn't establish that every intended word was synthesized or recorded. The [audio investigation](technical/workplace-english-audio-diagnosis.md) and [recording checks](verification/workplace-english-release-checks.md#walkthrough-audio-correction) describe the separate delivery and content checks.
- **Keep deployment small.** Redis holds temporary state, and the agent process also coordinates assessments. Four Compose services keep local setup manageable, but history is lost if Redis restarts and background work cannot yet scale independently.

## Data, ownership, and recovery

- **History belongs to one browser guest.** A signed HttpOnly cookie identifies the guest. Reads and changes are checked against that identity, and session ownership protects against competing tabs.
- **Retention follows practice activity.** Session text expires within 24 hours of eligible practice activity by default. Reads, heartbeats, and result writes don't extend that time. Delete removes the application's session data.
- **The application doesn't save learner recordings.** Current-answer audio stays in bounded memory and is released after acceptance or discard. Agent recording and telemetry are disabled, and application logs exclude learner content.
- **Accepted work survives API or agent restarts.** Redis retains the saved session while those processes restart. An interrupted voice session returns paused, and the learner repeats any unsent answer. Pending assessment can finish in the background. Redis itself has persistence disabled, so restarting it loses that data.
- **Answers have a time limit.** A cue appears at 60 seconds; at 120 seconds the learner chooses **Use this answer** or **Try again**. **I wasn't finished** extends the previous answer using its remaining allowance. If the model infers a continuation instead, the combined limit is checked after capture, so that new interval can run longer before being rejected.

## Scaling to 10,000 concurrent sessions

The default is four active voice sessions. These are proposed changes, not implemented scaling features or load-test results:

- **Scale each kind of work separately.** Run API/SSE replicas, voice workers, and assessment workers independently. Measure CPU and memory per voice session, keep workers warm, and let active conversations finish during deployment or scale-down. [LiveKit distributes jobs across available agent servers](https://docs.livekit.io/deploy/custom/deployments/).
- **Remove the shared Redis bottleneck.** Session updates currently watch a global admission key that every heartbeat changes. Unrelated learners can cause transaction retries. Separate capacity allocation from session updates, then partition state by guest so ownership checks stay local. Use replicated Redis with a defined failover policy while preserving expiry and deletion.
- **Replace polling with notifications.** Each UI stream checks state every 500 ms. At 10,000 open streams, that is roughly 20,000 checks per second before agent traffic. Use existing change notifications to trigger reads, with periodic reconciliation and a fresh snapshot after reconnecting.
- **Give assessments a work queue.** Replace session scans with queued session and assessment IDs. Workers would check the saved session and claim the matching attempt before processing it. Enqueue work atomically with the state change, and retry abandoned claims without saving duplicate or outdated results.
- **Budget provider capacity and measure the limits.** Plan for [LiveKit participant limits, STT/TTS connections, and LLM request/token quotas](https://docs.livekit.io/deploy/admin/quotas-and-limits/). Admission control should protect ongoing conversations when capacity is full. Increase load gradually and test worker crashes, Redis failover, and reconnect bursts while tracking p95/p99 reply latency, queue age, errors, and cost per session.

## What still needs evaluation

- Coaching usefulness and scoring consistency across varied accents and responses.
- Physical phone microphones, acoustic echo, and the supported browser/device combinations.
- Reply latency under realistic load and recovery from provider failures.
- Whether the added waiting time from complete-reply buffering is acceptable to learners.

The [verification record](verification/workplace-english-release-checks.md) separates completed checks from these open questions. Earlier product and architecture proposals are available in the [documentation index](README.md#development-history).
