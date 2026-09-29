"""Bounded, restartable work discovery in the existing agent service."""

import asyncio

from app.assessment.service import assess
from app.assessment.targeted import assess_retry
from app.sessions.models import Session
from app.sessions.recovery import expire_assessment, recover, sweep_rooms
from app.sessions.repository import Unavailable


class WorkCoordinator:
    def __init__(self, repo, gateway):
        self.repo, self.gateway = repo, gateway
        self.cursor = 0
        self.tasks = {}

    async def cycle(self):
        for key, (saved, request, retry_id, task) in list(self.tasks.items()):
            if task.done():
                if not task.cancelled():
                    task.exception()
                del self.tasks[key]
                continue
            try:
                current = await self.repo.get(saved.guest_id, saved.id)
                assessment = (
                    next(r for r in current.retries if r.id == retry_id).assessment
                    if retry_id
                    else current.assessment
                )
                if assessment.request_id != request or assessment.status not in (
                    "pending",
                    "running",
                ):
                    task.cancel()
            except Unavailable:
                task.cancel()

        # Carry the SCAN cursor across cycles; restarting at zero can starve later records.
        self.cursor, keys = await self.repo.redis.scan(
            self.cursor, match="guest:*:session:*", count=32
        )
        for key in keys:
            raw = await self.repo.redis.get(key)
            if not raw:
                continue
            saved = Session.model_validate_json(raw)
            if saved.expires_at <= self.repo.clock():
                continue
            try:
                await recover(self.repo, saved.guest_id, saved.id)
                saved = await self.repo.update(
                    saved.guest_id,
                    saved.id,
                    lambda s: expire_assessment(s, self.repo.clock()),
                )
            except Unavailable:
                continue
            for retry_id, assessment in [(None, saved.assessment)] + [
                (r.id, r.assessment) for r in saved.retries
            ]:
                task_key = f"{key}:{retry_id or 'original'}"
                if (
                    assessment.status == "pending"
                    and task_key not in self.tasks
                    and len(self.tasks) < 4
                ):
                    task = asyncio.create_task(
                        assess_retry(self.repo, saved, retry_id)
                        if retry_id
                        else assess(self.repo, saved)
                    )
                    self.tasks[task_key] = saved, assessment.request_id, retry_id, task
        await sweep_rooms(self.repo, self.gateway)

    async def close(self):
        for *_, task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*(task for *_, task in self.tasks.values()), return_exceptions=True)
