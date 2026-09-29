import os
import time
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.config import Settings
from app.sessions.models import Session
from app.sessions.repository import Repository


@pytest.fixture
def config():
    return Settings(
        guest_cookie_secret="test-secret-" * 4,
        livekit_url="wss://example.livekit.cloud",
        livekit_api_key="test",
        livekit_api_secret="test",
    )


@pytest.fixture
def session():
    now = time.time()
    return Session(
        guest_id=uuid4().hex,
        purpose_id="welcome-everyone",
        content_version="test",
        conversation_model="test",
        created_at=now,
        last_practice_at=now,
        expires_at=now + 86400,
    )


@pytest.fixture
async def repo(config):
    redis = Redis.from_url(
        os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/15"), decode_responses=True
    )
    # Integration tests must fail if their advertised real datastore isn't available.
    await redis.ping()
    repository = Repository(redis, config)
    namespace = uuid4().hex
    repository.capacity_key = f"test:{namespace}:admission"
    repository.rooms_key = f"test:{namespace}:rooms"
    yield repository
    await redis.delete(repository.capacity_key, repository.rooms_key)
    await redis.aclose()
