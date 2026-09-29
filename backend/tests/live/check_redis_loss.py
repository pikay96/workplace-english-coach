"""Restart only the disposable test Redis; never erase the application's temporary history."""

import os
import subprocess
import time

from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app.api.main import create_app
from app.config import Settings
from app.sessions.models import new_id
from app.sessions.repository import Repository

config = Settings(
    guest_cookie_secret="fixture-only-" * 4,
    livekit_url="wss://example.livekit.cloud",
    livekit_api_key="fixture",
    livekit_api_secret="fixture",
)
redis = Redis.from_url(
    os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/15"), decode_responses=True
)
with TestClient(create_app(config, Repository(redis, config))) as client:
    headers = {"origin": config.app_origin}
    client.post("/api/guest", json={}, headers=headers)
    saved = client.post(
        "/api/sessions",
        json={"purpose_id": "welcome-everyone", "command_id": new_id()},
        headers=headers,
    ).json()
    subprocess.run(
        ["docker", "restart", "workplace-english-test-redis"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    time.sleep(1)
    missing = client.get(f"/api/sessions/{saved['id']}")
    assert missing.status_code == 404 and missing.json()["code"] == "session_unavailable"
    assert client.get("/api/sessions").json() == []
    print("Redis process loss: old session unavailable; no fabricated history or resurrection")
