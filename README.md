# Workplace English

A real-time voice tutor for B1–B2 English learners who want to feel more comfortable in everyday work conversations. Practice with Alex, get feedback on your wording, and try one suggestion in a short follow-up.

[Watch the walkthrough](demo/walkthrough.mp4) · [AI workflow](workflow.md) · [Assignment](PROMPT.md)

## Run with Docker Compose

You'll need Docker with Compose, an internet connection, and a LiveKit Cloud project with Inference access and available credits. You don't need Python, Node, or the LiveKit CLI installed on your machine.

1. Copy `.env.example` to `.env` in the repository root.
2. Fill in `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `GUEST_COOKIE_SECRET`. Generate the cookie secret with this command and paste its output into `.env`:

   ```sh
   docker run --rm python:3.12.12-slim-bookworm python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Build and start the services:

   ```sh
   docker compose up --build -d
   docker compose ps
   ```

4. Open [localhost:8080](http://localhost:8080). Choose a scenario and purpose, read the disclosure, select **Start practice**, and allow microphone access. Wait for **Your turn** before speaking. Headphones help avoid echo.

Compose reads configuration from the root `.env` and passes it to the services. All model calls use LiveKit Inference, so separate Gemini, Deepgram, and Cartesia API keys aren't needed.

A few setup details:

- The first build downloads dependencies and turn-detector assets, so it takes longer than later builds.
- If you change the port, update both `APP_PORT` and `APP_ORIGIN`. Keep `REDIS_URL=redis://redis:6379/0` when using the included Redis service.
- Access from a phone or another computer needs trusted HTTPS, a matching `APP_ORIGIN`, and `COOKIE_SECURE=true`. A plain HTTP LAN address won't support microphone access.
- **History is temporary.** Restarting Redis, or running `docker compose down`, loses saved sessions because Redis persistence is disabled.

To check provider access, run:

```sh
docker compose exec api python -m app.voice.preflight
```

This makes billable calls to test conversation, transcription, speech, and assessment using synthetic audio. The regular container health checks don't call models; `/health/ready` checks Redis and agent registration.

To inspect logs or stop the app:

```sh
docker compose logs --tail 50 api agent
docker compose down
```

## The tutoring experience

The goal is to leave each practice with one useful change to try in a real conversation.

- **Start with a specific situation.** Nine purposes across meetings, one-on-ones, and casual conversation give the learner a clear goal. Each includes a useful expression and examples they can hear before starting.
- **Keep practice short.** Alex asks an opening question and responds to the learner's answers. After two or three answers, the exchange moves into coaching.
- **Make feedback concrete.** Coaching quotes the learner's actual words and explains their naturalness and workplace tone. The learner can use their own phrasing; copying the suggested expression isn't required.
- **Try the advice immediately.** A focused retry takes one or two answers and targets a coaching suggestion. Its feedback stays separate from the original scores.
- **Make it easy to return.** Recent sessions lets the same browser resume practice or review saved feedback without creating an account. Opening a completed review doesn't request microphone access.

## Architecture

Four services run in Compose:

| Service | Responsibility                                                                                                                                                                               |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`   | Serves the React/TypeScript interface and proxies API requests. The browser receives saved session updates over HTTP/SSE and connects to LiveKit for live audio.                             |
| `api`   | FastAPI handles guest identity, session commands, history, and room dispatch. It also serves speech for examples, hints, and saved review.                                                   |
| `agent` | A Python LiveKit worker handles the live conversation, Silero voice activity detection, local turn detection, Deepgram transcription, and Cartesia speech. It also runs pending assessments. |
| `redis` | Stores conversations, accepted answers, session ownership, command receipts, and assessment results. Atomic transactions protect updates from competing requests.                            |

The backend separates [session state and ownership](backend/app/sessions/), [conversation prompts and context](backend/app/conversation/), [assessment and evidence validation](backend/app/assessment/), and [voice/provider integration](backend/app/voice/). Both the API and agent use the same session rules; the browser displays the state saved by the backend.

The live path is **learner audio → transcription → Gemini response → Cartesia speech**, transported through LiveKit. A separate Gemini request assesses the saved exchange. Models, voice, and speech speed are configurable in `.env`; Alex currently uses Parker at a `TTS_SPEED` of `0.8`.

## Decisions and tradeoffs

- **Use a transcript-based voice pipeline.** Having the words available before speech makes validation, replay, and feedback easier to inspect. It also adds transcription and synthesis steps to the response path. LiveKit Cloud handles media transport, while the application services run locally in Docker.
- **Let the model choose the words; let code control the session.** The model proposes replies and coaching. Application code validates them, counts accepted answers, and controls transitions. Saved command IDs and ownership checks prevent duplicate actions and stale tabs from changing the session. That takes more code, but makes retries and recovery predictable.
- **Assess wording only.** Naturalness and Workplace tone are based on transcripts, with quotes checked against accepted answers. This version doesn't assess pronunciation, fluency, or vocal delivery. A separate assessment request gives coaching its own rubric and context, at the cost of another model call.
- **Take turns speaking.** Alex finishes before the microphone opens for the learner. This keeps the speaking state clear, but it means the learner can't interrupt by talking. Pause and Finish can still stop playback; Pause discards an unsent answer.
- **Prepare the full reply before playback.** This prevents gaps between incoming TTS chunks from reaching playback, at the cost of a longer wait before Alex starts. It does not establish that the synthesized or recorded speech contains every intended word; that needs a separate audio check.
- **Keep the demo deployment small.** Redis holds temporary conversation state, and the agent service also coordinates assessments. This keeps setup to four services, but history is lost if Redis restarts and background work cannot yet scale independently.

## Scaling to 10,000 concurrent sessions

The demo defaults to four active voice sessions and hasn't been tested at this scale. Before increasing capacity, I would:

- **Scale each kind of work separately.** Run API/SSE replicas, voice workers, and assessment workers independently. Measure CPU and memory per voice session, keep workers warm, and let active conversations finish when deploying or scaling down. [LiveKit distributes jobs across available agent servers](https://docs.livekit.io/deploy/custom/deployments/).
- **Remove the shared Redis bottleneck.** Session updates currently watch a global admission key that every heartbeat changes. Unrelated learners can therefore cause transaction retries. Separate capacity allocation from session updates, then partition state by guest so ownership checks stay local. Use replicated Redis with a defined failover policy while preserving expiry and deletion.
- **Replace polling with notifications.** The UI stream checks state every 500 ms; 10,000 open streams would mean roughly 20,000 checks per second before agent traffic. Use the existing change notifications to trigger reads, with periodic reconciliation and a fresh snapshot after reconnecting.
- **Give assessments a work queue.** Replace session scans with queued session and assessment IDs. Workers would check the saved session and claim the matching attempt before processing it. Enqueue work atomically with the state change, and retry abandoned claims without saving duplicate or outdated results.
- **Budget provider capacity and prove the limits.** Plan for [LiveKit participant limits, STT/TTS connections, and LLM request/token quotas](https://docs.livekit.io/deploy/admin/quotas-and-limits/). Admission control should protect ongoing conversations when capacity is full. Increase test load gradually and exercise worker crashes, Redis failover, and reconnect bursts while tracking p95/p99 reply latency, queue age, errors, and cost per session.

## Data and known limits

- **Temporary, browser-scoped history.** A signed HttpOnly cookie identifies the guest. Session text expires within 24 hours of eligible practice activity; reads, heartbeats, and result writes don't extend it. Delete removes the application's session data.
- **No saved learner recordings.** Current-answer audio stays in bounded memory and is released after acceptance or discard. Agent recording and telemetry are disabled; application logs exclude learner content.
- **Recovery preserves accepted work.** Restarting the API or agent leaves Redis data intact. An interrupted voice session returns paused, and the learner must repeat any unsent answer. A pending assessment can finish in the background.
- **Answers have a time limit.** A cue appears at 60 seconds; at 120 seconds the learner chooses **Use this answer** or **Try again**. **I wasn't finished** extends the previous answer using its remaining allowance. If the model infers a continuation instead, the combined limit is checked after capture, so that new interval can run longer before being rejected.
- **Human evaluation remains open.** Automated checks and the demo use synthetic learner speech. Coaching quality, varied accents, physical phone microphones, echo behavior, and response-latency percentiles still need evaluation.

## Verification

Recorded checks cover Compose startup from a separate checkout, all four provider routes, backend and frontend tests, browser history isolation, and a real WebRTC practice/coaching/review journey. The [verification record](docs/verification/workplace-english-release-checks.md) describes the results and their limits.

The walkthrough uses scripted synthetic learner audio through the running application. Alex's replies, transcripts, and feedback are generated during the recording. See [demo notes](demo/README.md) for what it demonstrates and how to try the same flow yourself.

### Run the development checks

Application dependencies are pinned in lockfiles. Python and npm package mirrors are configured in `backend/pyproject.toml` and `frontend/.npmrc`.

For backend checks, install Python 3.12 and uv 0.11.18, then run:

```sh
docker run --rm -d --name workplace-english-test-redis -p 127.0.0.1:6380:6379 redis:7.4.9-alpine redis-server --save "" --appendonly no
cd backend
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run python export_openapi.py
```

Tests use a real Redis on localhost:6380, database 15, with separate guest keys per test. Set `TEST_REDIS_URL` to override the address.

For frontend checks, use Node 22. From the repository root:

```sh
cd frontend
npm ci
npm run types:api
npm test
npm run build
npm run test:browser
```

Playwright defaults to installed Microsoft Edge. Most browser tests use HTTP fixtures. To include the history check against the running app, set `TEST_APP_URL=http://localhost:8080`.

The optional live voice suite uses real WebRTC and billable LiveKit Inference calls. From `frontend/` in PowerShell:

```powershell
$env:LIVE_VOICE_TEST='1'
$env:TEST_APP_URL='http://localhost:8080'
npm run test:browser -- live-voice.spec.ts
```

On Windows, the suite generates learner speech in memory using an installed English System.Speech voice. The answer-cap test takes at least four minutes because it crosses the 120-second boundary twice. The non-Windows fallback requires `TEST_PYTHON` and Inference access for fixture generation; that full path hasn't been validated.

## Submission files

- [PROMPT.md](PROMPT.md): the assignment.
- [workflow.md](workflow.md): AI tools, models, and how they were used.
- [docs/README.md](docs/README.md): research, brainstorming, design handoff notes, specifications, implementation plans, milestone checkpoints, and investigation notes behind the workflow.
- [demo/walkthrough.mp4](demo/walkthrough.mp4): the recorded interface and voice agent.
- [.env.example](.env.example): runtime configuration, without credentials.

The submission ZIP includes the source, Git history, written workflow documents, and final walkthrough video. The design prototype and its previews and sample audio are excluded, along with credentials, installed dependencies, caches, raw recordings, and video-production scripts.
