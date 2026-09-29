from contextlib import suppress
from math import ceil

from redis.exceptions import WatchError

from app.sessions.models import new_id
from app.sessions.recovery import pause_lost_owner
from app.sessions.repository import Repository
from app.sessions.transitions import Rejected, activity


async def claim(repo: Repository, guest: str, identifier: str, gateway):
    """Reserve capacity and fence old ownership before authorizing a fresh publisher."""
    epoch = new_id()
    lease, key = repo.lease(guest), repo.key(guest, identifier)
    staged = f"{identifier}:{epoch}:claiming"
    active = f"{identifier}:{epoch}:active"
    room, participant = f"practice-{identifier}-{epoch}", f"learner-{epoch}"
    old_room = None
    for _ in range(12):
        async with repo.redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(lease, key, repo.capacity_key)
                session = repo.parse(await pipe.get(key), guest)
                if session.lifecycle == "completed":
                    raise Rejected("completed")
                owner = await pipe.get(lease)
                old_key, old_session = key, session
                if owner:
                    old_key = repo.key(guest, owner.split(":")[0])
                    await pipe.watch(old_key)
                    raw = await pipe.get(old_key)
                    if raw:
                        old_session = repo.parse(raw, guest)
                    else:
                        old_key = key
                old_room = old_session.room
                now = repo.clock()
                occupied = set(await pipe.zrangebyscore(repo.capacity_key, f"({now}", "+inf"))
                occupied.discard(old_room)
                if len(occupied) >= repo.config.max_active_sessions:
                    raise Rejected("capacity_full")
                pause_lost_owner(old_session)
                old_session.revision += 1
                old_session.sequence += 1
                pipe.multi()
                pipe.zremrangebyscore(repo.capacity_key, "-inf", now)
                if old_room:
                    pipe.zrem(repo.capacity_key, old_room)
                    pipe.zadd(repo.rooms_key, {old_room: now})
                deadline = min(session.expires_at, now + repo.config.voice_lease_seconds)
                pipe.zadd(repo.capacity_key, {room: deadline})
                pipe.zadd(repo.rooms_key, {room: deadline})
                pipe.set(lease, staged, ex=repo.config.voice_lease_seconds)
                pipe.set(old_key, old_session.model_dump_json(), exat=ceil(old_session.expires_at))
                await pipe.execute()
                break
            except WatchError:
                continue
    else:
        raise Rejected("busy")

    try:
        if old_room:
            await gateway.remove_room(old_room)
            await repo.redis.zrem(repo.rooms_key, old_room)
        for _ in range(12):
            async with repo.redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(lease, key, repo.capacity_key)
                    deadline = await pipe.zscore(repo.capacity_key, room)
                    if await pipe.get(lease) != staged or not deadline or deadline <= repo.clock():
                        raise Rejected("stale_connection")
                    session = repo.parse(await pipe.get(key), guest)
                    if session.lifecycle == "completed":
                        raise Rejected("completed")
                    session.connection_epoch, session.room, session.participant = (
                        epoch,
                        room,
                        participant,
                    )
                    session.lifecycle, session.substate = "in_progress", "connecting"
                    session.input, session.pending_command = None, None
                    session.generation_id = new_id()
                    activity(session, repo.clock(), repo.config.session_ttl_seconds)
                    session.revision += 1
                    session.sequence += 1
                    pipe.multi()
                    pipe.set(key, session.model_dump_json(), exat=ceil(session.expires_at))
                    pipe.set(lease, active, ex=repo.config.voice_lease_seconds)
                    deadline = min(
                        session.expires_at, repo.clock() + repo.config.voice_lease_seconds
                    )
                    pipe.zadd(repo.capacity_key, {room: deadline})
                    pipe.zadd(repo.rooms_key, {room: deadline})
                    repo.index_write(pipe, session)
                    await pipe.execute()
                    await gateway.dispatch(session)
                    # Dispatch can outlive Pause, Delete, another claim, or the lease.
                    await repo.update(guest, identifier, lambda s: None, epoch=epoch)
                    return session, gateway.token(session)
                except WatchError:
                    continue
        raise Rejected("busy")
    except BaseException:
        with suppress(Exception):
            await repo.redis.eval(
                "local v=redis.call('GET',KEYS[1]); if v==ARGV[1] or v==ARGV[2] then "
                "redis.call('DEL',KEYS[1]) end; redis.call('ZREM',KEYS[2],ARGV[3]); "
                "redis.call('ZADD',KEYS[3],ARGV[4],ARGV[3]); return 1",
                3,
                lease,
                repo.capacity_key,
                repo.rooms_key,
                staged,
                active,
                room,
                repo.clock(),
            )
            await repo.update(guest, identifier, pause_lost_owner, orphaned=True)
        # Even a partially successful dispatch must not leave a live room behind.
        with suppress(Exception):
            await gateway.remove_room(room)
            await repo.redis.zrem(repo.rooms_key, room)
        raise
