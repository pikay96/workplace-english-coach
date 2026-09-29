"""Explicit Compose restart gate. Run while no learner call is active."""

import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]


def docker(*args, script=None):
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        input=script,
        text=True,
        capture_output=True,
        check=True,
        timeout=90,
    ).stdout


def wait(check, seconds=100):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            result = check()
            if result:
                return result
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise AssertionError("Recovery deadline exceeded")


with httpx.Client(
    base_url="http://localhost:8080", headers={"Origin": "http://localhost:8080"}, timeout=20
) as client:
    client.post("/api/guest", json={}).raise_for_status()
    created = client.post(
        "/api/sessions",
        json={"purpose_id": "welcome-everyone", "command_id": __import__("uuid").uuid4().hex},
    )
    created.raise_for_status()
    saved = created.json()
    path = f"/api/sessions/{saved['id']}"
    try:
        docker("restart", "api")
        wait(lambda: client.get("/health/live").is_success)
        restored = client.get(path).json()
        assert restored["id"] == saved["id"] and restored["expires_at"] == saved["expires_at"]
        print("API restart: temporary session and absolute expiry preserved", flush=True)
        wait(lambda: client.get("/health/ready").is_success)
        connected = client.post(path + "/connect", json={})
        connected.raise_for_status()
        saved = connected.json()["session"]  # Never print the token.
        docker("stop", "agent")
        # Synthetic frozen wording plus a lost capped input; no learner content is used.
        seed = """
import asyncio
from redis.asyncio import Redis
from app.config import settings
from app.sessions.repository import Repository
from app.sessions.models import Answer, Transcript, Input, TutorMessage, new_id
from app.sessions.transitions import freeze
async def main():
    config=settings()
    redis=Redis.from_url(config.redis_url.get_secret_value(),decode_responses=True)
    repo=Repository(redis,config)
    def change(s):
        prompt=TutorMessage(generation_id=s.generation_id,kind="opening",
            text="Please welcome the team.",delivery="completed",
            played_text="Please welcome the team.")
        s.messages=[prompt]
        s.question_id=prompt.id
        words="Good morning, everyone. Thank you for making the time. "
        words+="Today let's agree on the next steps."
        s.answers=[Answer(input_id=new_id(),question_id=prompt.id,capture_seconds=8,
            transcript=Transcript(text=words,source_identity="synthetic-restart-fixture"))]
        s.input=Input(status="awaiting_limit_confirmation",first_speech_at=repo.clock())
        s.phase="coaching"
        freeze(s)
    result=await repo.update(GUEST,IDENTIFIER,change)
    print(result.expires_at)
    await redis.aclose()
asyncio.run(main())
"""
        seed = f"GUEST={saved['guest_id']!r}\nIDENTIFIER={saved['id']!r}\n" + seed
        expiry = float(docker("exec", "-T", "api", "python", "-", script=seed).strip())
        docker("start", "agent")

        def recovered():
            response = client.get(path)
            response.raise_for_status()
            current = response.json()
            if current["assessment"]["status"] == "unavailable":
                raise AssertionError("Real recovered assessment unavailable")
            return current if current["assessment"]["status"] == "ready" else None

        result = wait(recovered)
        assert result["lifecycle"] == "paused" and result["input"] is None
        assert result["expires_at"] == expiry and len(result["answers"]) == 1
        assert len(result["messages"]) == 1  # No unauthorized coaching autoplay.
        assert result["messages"][0]["text"] == "Please welcome the team."
        print(
            "Agent restart: capped input discarded, prompt preserved, "
            "pending assessment completed without Resume or autoplay",
            flush=True,
        )
    finally:
        docker("start", "agent")
        client.delete(path)
