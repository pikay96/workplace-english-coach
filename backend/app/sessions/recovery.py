"""Recovery uses canonical evidence; no read can recreate a missing session."""

from app.sessions.transitions import cancel_output, freeze


def pause_lost_owner(session):
    if session.lifecycle != "in_progress":
        return
    lost_input = session.input is not None and (
        session.input.first_speech_at is not None or session.input.status != "open"
    )
    session.lifecycle = "paused"
    session.input = None
    session.pending_command = None
    cancel_output(session)
    if session.phase in ("coaching", "retry"):
        freeze(session)
    session.notice = (
        "Connection ended. Your unsent answer was not saved. Resume to repeat the same prompt."
        if lost_input
        else "Connection ended. Your accepted answers are saved. Resume when ready."
    )


async def recover(repo, guest, identifier):
    # Watch the lease so an earlier GET cannot pause a concurrent successful Resume.
    return await repo.update(guest, identifier, pause_lost_owner, orphaned=True)


def expire_assessment(session, now):
    if (
        session.helper
        and session.helper.status == "running"
        and session.helper.deadline
        and session.helper.deadline <= now
    ):
        session.helper.status = "unavailable"
    for retry in session.retries:
        if (
            retry.assessment.status == "running"
            and retry.assessment.deadline is not None
            and retry.assessment.deadline <= now
        ):
            retry.assessment.status = "unavailable"
            if session.phase == "retry":
                session.substate = "unavailable"
    assessment = session.assessment
    if (
        assessment.status == "running"
        and assessment.deadline is not None
        and assessment.deadline <= now
    ):
        assessment.status = "unavailable"
        assessment.error = "Assessment did not finish. Retry from your saved words."
        if session.phase == "coaching":
            session.substate = "unavailable"


async def sweep_rooms(repo, gateway):
    """Fence expired reservations before revocation; a heartbeat cannot revive them."""
    expired = await repo.redis.zrangebyscore(repo.rooms_key, "-inf", repo.clock(), start=0, num=32)
    for room in expired:
        claimed = await repo.redis.eval(
            "local score=redis.call('ZSCORE',KEYS[1],ARGV[1]); "
            "if score and tonumber(score)<=tonumber(ARGV[2]) then "
            "redis.call('ZREM',KEYS[2],ARGV[1]); return 1 end return 0",
            2,
            repo.rooms_key,
            repo.capacity_key,
            room,
            repo.clock(),
        )
        if claimed:
            await gateway.remove_room(room)
            await repo.redis.zrem(repo.rooms_key, room)
