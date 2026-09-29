import asyncio
import json
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.auth import establish, guest
from app.config import Settings, settings
from app.content import Content, content, purpose
from app.conversation.helpers import generate_hint
from app.observability import configure_logs, failure
from app.sessions.models import Command, Identifier, Model, Session
from app.sessions.ownership import claim
from app.sessions.recovery import recover
from app.sessions.repository import Repository, Unavailable
from app.sessions.transitions import Rejected, command
from app.voice.http_audio import response as audio_response


class CreateSession(Model):
    purpose_id: str
    command_id: Identifier
    source_session_id: Identifier | None = None


class ConnectResult(Model):
    session: Session
    url: str
    token: str


class Heartbeat(Model):
    connection_epoch: str


class Playback(Model):
    message_id: str


class ExpressionPlayback(Model):
    expression_id: Literal["expression", "alternative", "example"]


def create_app(
    config: Settings | None = None, repository: Repository | None = None, gateway=None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        from app.voice.gateway import Gateway

        configure_logs()
        app.state.config = config or settings()
        app.state.repo = repository or Repository(
            Redis.from_url(
                app.state.config.redis_url.get_secret_value(),
                decode_responses=True,
                socket_timeout=3,
                socket_connect_timeout=3,
            ),
            app.state.config,
        )
        app.state.gateway = gateway or Gateway(app.state.config)
        yield
        if not repository:
            await app.state.repo.redis.aclose()

    app = FastAPI(title="Workplace English", version="1.0.0", lifespan=lifespan)

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("origin") != app.state.config.app_origin:
                return JSONResponse(
                    {"code": "origin_rejected"},
                    status_code=403,
                    headers={"Cache-Control": "no-store"},
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(Rejected)
    async def rejected(request, error):
        return JSONResponse(
            {"code": error.code}, status_code=404 if isinstance(error, Unavailable) else 409
        )

    @app.exception_handler(RedisError)
    async def redis_error(request, error):
        return JSONResponse({"code": "storage_unavailable"}, status_code=503)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        return JSONResponse({"code": "invalid_request"}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request, error):
        failure("api_unavailable", error)
        return JSONResponse({"code": "service_unavailable"}, status_code=503)

    @app.get("/health/live")
    async def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready():
        repo = app.state.repo
        await repo.redis.ping()
        registration = await repo.redis.get("agent:registered")
        if not registration or repo.clock() - float(registration) > 15:
            return JSONResponse({"status": "agent_unavailable"}, status_code=503)
        return {"status": "ready"}

    @app.get("/api/content", response_model=Content)
    async def get_content():
        return content()

    @app.post("/api/guest")
    async def new_guest(request: Request, response: Response):
        establish(request, response)
        return {"available": True}

    @app.post("/api/sessions", response_model=Session)
    async def create(value: CreateSession, owner: str = Depends(guest)):
        try:
            selected = purpose(value.purpose_id)
        except StopIteration:
            raise HTTPException(422, "purpose_unavailable") from None
        if not selected.integrated:
            raise HTTPException(422, "purpose_not_in_checkpoint")
        repo = app.state.repo
        now = repo.clock()
        session = Session(
            guest_id=owner,
            purpose_id=selected.purpose_id,
            content_version=content().version,
            conversation_model=app.state.config.conversation_model,
            created_at=now,
            last_practice_at=now,
            expires_at=now + app.state.config.session_ttl_seconds,
        )
        if value.source_session_id:
            source = await repo.get(owner, value.source_session_id)
            if source.lifecycle != "completed" or source.purpose_id != selected.purpose_id:
                raise Rejected("invalid_source_session")
            session.source_session_id = source.id
            session.previous_opening = next(
                (m.text for m in source.messages if m.kind == "opening"), None
            )
        return await repo.create(session, value.command_id)

    async def snapshot(owner: str, identifier: str):
        return await recover(app.state.repo, owner, identifier)

    @app.get("/api/sessions", response_model=list[Session])
    async def sessions(owner: str = Depends(guest)):
        saved = await app.state.repo.list(owner)
        return [await snapshot(owner, s.id) for s in saved]

    @app.get("/api/sessions/{identifier}", response_model=Session)
    async def get_session(identifier: Identifier, owner: str = Depends(guest)):
        return await snapshot(owner, identifier)

    @app.post("/api/sessions/{identifier}/connect", response_model=ConnectResult)
    async def connect(identifier: Identifier, owner: str = Depends(guest)):
        if not await app.state.repo.redis.get("agent:registered"):
            raise HTTPException(503, "agent_unavailable")
        session, token = await claim(app.state.repo, owner, identifier, app.state.gateway)
        return ConnectResult(session=session, token=token, url=app.state.config.livekit_url)

    @app.post("/api/sessions/{identifier}/commands", response_model=Session)
    async def apply_command(identifier: Identifier, value: Command, owner: str = Depends(guest)):
        repo = app.state.repo
        result = await repo.update(
            owner,
            identifier,
            lambda s: command(s, value, repo.clock(), app.state.config.session_ttl_seconds),
        )
        if result.helper and result.helper.status == "pending":
            return await generate_hint(repo, result)
        return result

    @app.post("/api/sessions/{identifier}/heartbeat")
    async def heartbeat(identifier: Identifier, value: Heartbeat, owner: str = Depends(guest)):
        await app.state.repo.heartbeat(owner, identifier, value.connection_epoch)
        return {"status": "active"}

    @app.delete("/api/sessions/{identifier}", status_code=204)
    async def delete(identifier: Identifier, owner: str = Depends(guest)):
        session = await app.state.repo.delete(owner, identifier)
        if session and session.room:
            await app.state.gateway.remove_room(session.room)
        return Response(status_code=204)

    @app.get("/api/sessions/{identifier}/events")
    async def events(identifier: Identifier, request: Request, owner: str = Depends(guest)):
        await snapshot(owner, identifier)

        async def updates():
            last = -1  # Every connection starts with canonical state, including after an event gap.
            while not await request.is_disconnected():
                try:
                    session = await snapshot(owner, identifier)
                    if session.sequence != last:
                        event = {
                            "schema_version": 1,
                            "session_id": identifier,
                            "revision": session.revision,
                            "sequence": session.sequence,
                            "connection_epoch": session.connection_epoch,
                            "type": "snapshot",
                            "snapshot": session.model_dump(),
                        }
                        yield (
                            f"id: {session.sequence}\nevent: snapshot\n"
                            f"data: {json.dumps(event)}\n\n"
                        )
                        last = session.sequence
                    else:
                        yield ": keepalive\n\n"
                except (Unavailable, RedisError):
                    yield 'event: unavailable\ndata: {"code":"session_unavailable"}\n\n'
                    return
                await asyncio.sleep(0.5)

        return StreamingResponse(
            updates(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
        )

    @app.post("/api/sessions/{identifier}/playback")
    async def playback(identifier: Identifier, value: Playback, owner: str = Depends(guest)):
        saved = await app.state.repo.get(owner, identifier)
        helper = (
            saved.lifecycle == "paused"
            and saved.helper
            and saved.helper.status == "ready"
            and saved.helper.id == value.message_id
            and saved.helper.generation_id == saved.generation_id
        )
        if helper:
            text = saved.helper.text
        elif saved.lifecycle != "completed":
            raise Rejected("review_only")
        elif value.message_id == "coaching" and saved.assessment.result:
            text = saved.assessment.result.spoken_summary
        elif value.message_id == "takeaway" and saved.assessment.result:
            text = saved.assessment.result.takeaway
        elif value.message_id == "reminder" and not saved.answers:
            text = purpose(saved.purpose_id).expression
        elif any(r.id == value.message_id and r.assessment.result for r in saved.retries):
            result = next(r.assessment.result for r in saved.retries if r.id == value.message_id)
            text = f"{result.observation} {result.suggestion} {result.modeled_example}"
        else:
            raise Rejected("playback_unavailable")

        async def authorize():
            current = await app.state.repo.get(owner, identifier)
            if helper and (
                current.lifecycle != "paused" or current.generation_id != saved.generation_id
            ):
                raise Rejected("stale_helper")

        return audio_response(app.state.config, text, authorize)

    @app.post("/api/content/{purpose_id}/playback")
    async def expression_playback(purpose_id: str, value: ExpressionPlayback):
        try:
            selected = purpose(purpose_id)
        except StopIteration:
            raise Rejected("playback_unavailable") from None
        text = getattr(selected, value.expression_id)

        return audio_response(app.state.config, text)

    return app


app = create_app()
