from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings
from app.sessions.models import new_id
from app.sessions.repository import Repository


def test_http_guest_origin_ownership_and_saved_review(config):
    import os

    from redis.asyncio import Redis

    def app():
        redis = Redis.from_url(
            os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/15"), decode_responses=True
        )
        return create_app(config, Repository(redis, config))

    with TestClient(app()) as client, TestClient(app()) as stranger:
        assert client.post("/api/guest").status_code == 403
        headers = {"origin": config.app_origin}
        response = client.post("/api/guest", json={}, headers=headers)
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"]
        assert client.get("/api/content").json()["purposes"][0]["purpose_id"] == "welcome-everyone"
        payload = {"purpose_id": "welcome-everyone", "command_id": new_id()}
        created = client.post("/api/sessions", json=payload, headers=headers)
        assert created.status_code == 200
        session = created.json()
        assert (
            client.post("/api/sessions", json=payload, headers=headers).json()["id"]
            == session["id"]
        )
        stranger.post("/api/guest", json={}, headers=headers)
        assert stranger.get(f"/api/sessions/{session['id']}").status_code == 404
        finished = client.post(
            f"/api/sessions/{session['id']}/commands",
            headers=headers,
            json={
                "command_id": new_id(),
                "expected_revision": session["revision"],
                "type": "finish",
            },
        )
        assert finished.status_code == 200
        assert finished.json()["lifecycle"] == "completed"
        review = client.get(f"/api/sessions/{session['id']}")
        assert review.headers["cache-control"] == "no-store"
        assert review.json()["answers"] == []
        assert review.json()["assessment"]["result"] is None
        assert client.delete(f"/api/sessions/{session['id']}", headers=headers).status_code == 204
        assert client.get(f"/api/sessions/{session['id']}").status_code == 404


def test_configuration_rejects_empty_secrets_and_excess_retention():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as error:
        Settings(
            guest_cookie_secret="",
            livekit_url="",
            livekit_api_key="",
            livekit_api_secret="",
            session_ttl_seconds=90000,
        )
    assert "guest_cookie_secret" in str(error.value)
    assert "session_ttl_seconds" in str(error.value)
