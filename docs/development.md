# Development guide

Start with the [README quickstart](../README.md#run-locally) to run Workplace English Coach in Docker. This guide covers the additional setup details and development checks.

## Configuration and daily use

- Copy [`.env.example`](../.env.example) to `.env` in the repository root. Compose passes that configuration to the services.
- The first build downloads dependencies and turn-detector assets. Later builds can reuse those caches.
- If you change the port, update both `APP_PORT` and `APP_ORIGIN`. Keep `REDIS_URL=redis://redis:6379/0` when using the included Redis service.
- Access from a phone or another computer needs trusted HTTPS, a matching `APP_ORIGIN`, and `COOKIE_SECURE=true`. A plain HTTP LAN address won't support microphone access.
- Redis persistence is disabled. Restarting Redis or running `docker compose down` loses saved sessions.

From the repository root, inspect service status and logs:

```sh
docker compose ps
docker compose logs --tail 50 api agent
```

Stop the app with:

```sh
docker compose down
```

## Check provider access

Once the services are running, check all four model routes:

```sh
docker compose exec api python -m app.voice.preflight
```

- This makes billable conversation, transcription, speech synthesis, and assessment calls using synthetic audio.
- All routes use LiveKit Inference, so you need LiveKit credentials and available credits, but no separate Gemini, Deepgram, or Cartesia keys.
- Container health checks don't call models. `/health/ready` checks Redis and agent registration; a healthy app can still encounter a provider-access or quota failure.
- Models, voice, and speech speed are configurable in `.env`. Alex currently uses Parker at a `TTS_SPEED` of `0.8`.

## Backend checks

Use **Python 3.12** and **uv 0.11.18**. Run these commands from the repository root:

```sh
docker run --rm -d --name workplace-english-test-redis -p 127.0.0.1:6380:6379 redis:7.4.9-alpine redis-server --save "" --appendonly no
cd backend
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run python export_openapi.py
```

- Tests use a real Redis on localhost:6380, database 15, with separate guest keys per test. Set `TEST_REDIS_URL` to override the address.
- The suite covers session transitions, ownership, competing commands, recovery, expiry, deletion, and assessment evidence.
- `export_openapi.py` updates the API contract used to generate frontend types.

When finished, stop the test Redis container; `--rm` removes it after it stops:

```sh
docker stop workplace-english-test-redis
```

## Frontend checks

Use **Node 22**. Run these commands from the repository root:

```sh
cd frontend
npm ci
npm run types:api
npm test
npm run build
npm run test:browser
```

- `types:api` generates TypeScript types from `backend/openapi.json`. Run it after exporting a changed API contract.
- Unit tests cover client behavior and audio controls. Most browser tests use HTTP fixtures.
- Playwright uses an installed Microsoft Edge browser. With no `TEST_APP_URL`, it starts the frontend development server itself.
- To include the history check against the running app, set `TEST_APP_URL=http://localhost:8080` before running the browser suite. That check uses a separate browser guest and removes the records it creates.

Dependencies are pinned in lockfiles. The package mirrors are configured in [`backend/pyproject.toml`](../backend/pyproject.toml) and [`frontend/.npmrc`](../frontend/.npmrc).

## Optional live voice checks

The live suite uses real WebRTC and billable LiveKit Inference calls. Start the app first, then run this from `frontend/` in PowerShell:

```powershell
$env:LIVE_VOICE_TEST='1'
$env:TEST_APP_URL='http://localhost:8080'
npm run test:browser -- live-voice.spec.ts
```

- On Windows, the suite generates learner speech in memory using an installed English System.Speech voice.
- The answer-cap test takes at least four minutes because it crosses the 120-second boundary twice.
- The non-Windows fallback requires `TEST_PYTHON` and Inference access for fixture generation. That full path hasn't been validated.
- Synthetic speech helps repeat a conversation, but doesn't replace listening tests with physical microphones and varied accents.

The [verification record](verification/workplace-english-release-checks.md) describes previous results. The [walkthrough guide](../demo/README.md) gives a short flow to try by hand.
