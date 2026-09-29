import pytest

from app.sessions.models import new_id
from app.sessions.ownership import claim
from app.sessions.transitions import Rejected


@pytest.mark.redis
async def test_previous_media_revoked_before_new_owner(repo, session):
    await repo.create(session, new_id())
    events = []

    class Gateway:
        async def remove_room(self, room):
            events.append("removed")
            assert (await repo.redis.get(repo.lease(session.guest_id))).endswith(":claiming")

        async def dispatch(self, saved):
            events.append("dispatched")
            assert (await repo.redis.get(repo.lease(session.guest_id))).endswith(":active")

        def token(self, saved):
            return "test-scoped-token"

    first, _ = await claim(repo, session.guest_id, session.id, Gateway())
    old_epoch = first.connection_epoch
    second, _ = await claim(repo, session.guest_id, session.id, Gateway())
    assert events == ["dispatched", "removed", "dispatched"]
    assert second.connection_epoch != old_epoch
    with pytest.raises(Rejected):
        await repo.heartbeat(session.guest_id, session.id, old_epoch)
    expiry = second.expires_at
    await repo.heartbeat(session.guest_id, session.id, second.connection_epoch)
    assert (await repo.get(session.guest_id, session.id)).expires_at == expiry


@pytest.mark.redis
async def test_failed_removal_never_authorizes_publisher(repo, session):
    session.room = "old-room"
    await repo.create(session, new_id())

    class FailingGateway:
        async def remove_room(self, room):
            raise RuntimeError("unavailable")

        async def dispatch(self, saved):
            pytest.fail("Must not dispatch before revocation")

    with pytest.raises(RuntimeError):
        await claim(repo, session.guest_id, session.id, FailingGateway())
    assert await repo.redis.get(repo.lease(session.guest_id)) is None
