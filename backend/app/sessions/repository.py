"""Guest-scoped WATCH/MULTI transactions. Network work never executes in a transaction."""

import time
from collections.abc import Callable
from math import ceil

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import WatchError

from app.config import Settings
from app.sessions.models import Session
from app.sessions.transitions import Rejected


class Unavailable(Rejected):
    def __init__(self):
        super().__init__("session_unavailable")


class Repository:
    def __init__(self, redis: Redis, config: Settings, clock: Callable[[], float] = time.time):
        self.redis, self.config, self.clock = redis, config, clock
        self.capacity_key = "voice:admission"
        # Metadata only. Retained after lease expiry so the sweeper can revoke rooms.
        self.rooms_key = "voice:rooms"

    @staticmethod
    def key(guest: str, identifier: str) -> str:
        return f"guest:{{{guest}}}:session:{identifier}"

    @staticmethod
    def index(guest: str) -> str:
        return f"guest:{{{guest}}}:recent"

    @staticmethod
    def lease(guest: str) -> str:
        return f"guest:{{{guest}}}:voice"

    def index_write(self, pipe, session: Session):
        index = self.index(session.guest_id)
        pipe.zadd(index, {session.id: session.expires_at})
        # A late result for an older session cannot expire the index of a newer session.
        pipe.eval(
            "local top=redis.call('ZREVRANGE',KEYS[1],0,0,'WITHSCORES'); "
            "if #top>0 then return redis.call('EXPIREAT',KEYS[1],math.ceil(tonumber(top[2]))) end",
            1,
            index,
        )

    def parse(self, raw, guest: str) -> Session:
        if not raw:
            raise Unavailable()
        session = Session.model_validate_json(raw)
        if session.guest_id != guest or session.expires_at <= self.clock():
            raise Unavailable()
        return session

    async def get(self, guest: str, identifier: str) -> Session:
        return self.parse(await self.redis.get(self.key(guest, identifier)), guest)

    async def create(self, session: Session, command_id: str) -> Session:
        receipt_key = f"guest:{{{session.guest_id}}}:create:{command_id}"
        for _ in range(12):
            async with self.redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(receipt_key)
                    prior = await pipe.get(receipt_key)
                    if prior:
                        return await self.get(session.guest_id, prior)
                    pipe.multi()
                    pipe.set(
                        self.key(session.guest_id, session.id),
                        session.model_dump_json(),
                        exat=ceil(session.expires_at),
                    )
                    pipe.set(receipt_key, session.id, exat=ceil(session.expires_at))
                    self.index_write(pipe, session)
                    await pipe.execute()
                    return session
                except WatchError:
                    continue
        raise Rejected("busy")

    async def update(
        self,
        guest: str,
        identifier: str,
        mutate: Callable[[Session], object],
        *,
        epoch: str | None = None,
        generation: str | None = None,
        orphaned: bool = False,
    ) -> Session:
        key, lease = self.key(guest, identifier), self.lease(guest)
        for _ in range(12):
            async with self.redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(key, lease, self.capacity_key)
                    session = self.parse(await pipe.get(key), guest)
                    owner = await pipe.get(lease)
                    deadline = await pipe.zscore(self.capacity_key, session.room or "")
                    live = (
                        owner == f"{identifier}:{session.connection_epoch}:active"
                        and deadline is not None
                        and deadline > self.clock()
                    )
                    if orphaned and live:
                        return session
                    if epoch is not None:
                        if session.connection_epoch != epoch or not live:
                            raise Rejected("stale_connection")
                    if generation and generation != session.generation_id:
                        raise Rejected("stale_generation")
                    before = session.model_dump_json()
                    mutate(session)
                    if session.model_dump_json() == before:
                        return session
                    try:
                        # Mutating a Pydantic instance does not validate nested list/text limits.
                        session = Session.model_validate(session.model_dump())
                    except ValidationError:
                        raise Rejected("session_limit") from None
                    session.revision += 1
                    session.sequence += 1
                    pipe.multi()
                    pipe.set(key, session.model_dump_json(), exat=ceil(session.expires_at))
                    if session.lifecycle != "in_progress" and session.room:
                        pipe.zrem(self.capacity_key, session.room)
                        pipe.zadd(self.rooms_key, {session.room: self.clock()})
                        if owner == f"{identifier}:{session.connection_epoch}:active":
                            pipe.delete(lease)
                    self.index_write(pipe, session)
                    pipe.publish(f"{key}:changed", str(session.sequence))
                    await pipe.execute()
                    return session
                except WatchError:
                    continue
        raise Rejected("busy")

    async def list(self, guest: str) -> list[Session]:
        index = self.index(guest)
        await self.redis.zremrangebyscore(index, "-inf", self.clock())
        identifiers = await self.redis.zrevrange(index, 0, 99)
        sessions = []
        for identifier in identifiers:
            try:
                sessions.append(await self.get(guest, identifier))
            except Unavailable:
                await self.redis.zrem(index, identifier)
        return sorted(sessions, key=lambda s: s.last_practice_at, reverse=True)

    async def delete(self, guest: str, identifier: str) -> Session | None:
        key, lease = self.key(guest, identifier), self.lease(guest)
        for _ in range(12):
            async with self.redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(key, lease)
                    raw, owner = await pipe.get(key), await pipe.get(lease)
                    if not raw:
                        return None
                    session = self.parse(raw, guest)
                    pipe.multi()
                    pipe.delete(key)
                    pipe.zrem(self.index(guest), identifier)
                    if owner and owner.startswith(f"{identifier}:"):
                        pipe.delete(lease)
                    if session.room:
                        pipe.zrem(self.capacity_key, session.room)
                        pipe.zadd(self.rooms_key, {session.room: self.clock()})
                    pipe.publish(f"{key}:changed", "deleted")
                    await pipe.execute()
                    return session
                except WatchError:
                    continue
        raise Rejected("busy")

    async def heartbeat(self, guest: str, identifier: str, epoch: str):
        session = await self.get(guest, identifier)
        if session.lifecycle != "in_progress":
            raise Rejected("paused")
        ok = await self.redis.eval(
            "local score=redis.call('ZSCORE',KEYS[2],ARGV[3]); "
            "if redis.call('GET',KEYS[1]) == ARGV[1] and score "
            "and tonumber(score)>tonumber(ARGV[4]) and redis.call('EXISTS',KEYS[4])==1 then "
            "redis.call('EXPIRE',KEYS[1],ARGV[2]); "
            "redis.call('ZADD',KEYS[2],ARGV[5],ARGV[3]); "
            "redis.call('ZADD',KEYS[3],ARGV[5],ARGV[3]); return 1 else return 0 end",
            4,
            self.lease(guest),
            self.capacity_key,
            self.rooms_key,
            self.key(guest, identifier),
            f"{identifier}:{epoch}:active",
            self.config.voice_lease_seconds,
            session.room or "",
            self.clock(),
            min(session.expires_at, self.clock() + self.config.voice_lease_seconds),
        )
        if not ok:
            raise Rejected("stale_connection")
