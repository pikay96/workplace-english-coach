"""Named RTC jobs plus a bounded service-level assessment task runner."""

import asyncio
import json
import signal
import time
from contextlib import suppress

from livekit.agents import (
    AgentServer,
    AgentSession,
    APIConnectOptions,
    JobContext,
    JobProcess,
    room_io,
)
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from redis.asyncio import Redis

from app.assessment.coordinator import WorkCoordinator
from app.config import settings
from app.observability import configure_logs, failure, metric
from app.sessions.recovery import pause_lost_owner
from app.sessions.repository import Repository
from app.voice.gateway import Gateway
from app.voice.inference import Inference
from app.voice.runtime import ControlledAgent, Runtime


def prewarm(process: JobProcess):
    configure_logs()
    process.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Disable even pre-session crash-log upload before connecting or reading learner state.
    ctx.init_recording({"audio": False, "traces": False, "logs": False, "transcript": False})
    config = settings()
    configure_logs()
    redis = Redis.from_url(
        config.redis_url.get_secret_value(),
        decode_responses=True,
        socket_timeout=3,
        socket_connect_timeout=3,
    )
    repo = Repository(redis, config)
    voice = None
    runtime = None
    try:
        metadata = json.loads(ctx.job.metadata)
        saved = await repo.get(metadata["guest_id"], metadata["session_id"])
        epoch = metadata["connection_epoch"]
        lease = await redis.get(repo.lease(saved.guest_id))
        if (
            saved.connection_epoch != epoch
            or saved.room != ctx.room.name
            or lease != f"{saved.id}:{epoch}:active"
            or saved.lifecycle != "in_progress"
        ):
            return
        await ctx.connect()
        await asyncio.wait_for(ctx.wait_for_participant(identity=saved.participant), 25)
        models = Inference(config)
        voice = AgentSession(
            conn_options=SessionConnectOptions(
                stt_conn_options=APIConnectOptions(max_retry=0, timeout=8),
                tts_conn_options=APIConnectOptions(max_retry=0, timeout=8),
                max_unrecoverable_errors=0,
            ),
            stt=models.stt(),
            tts=models.tts(),
            vad=ctx.proc.userdata["vad"],
            turn_handling={
                "turn_detection": MultilingualModel(),
                "endpointing": {"min_delay": 1.2, "max_delay": 4.0},
                "interruption": {
                    "enabled": False,
                    "resume_false_interruption": False,
                    "discard_audio_if_uninterruptible": True,
                },
                "preemptive_generation": {"enabled": False, "preemptive_tts": False},
            },
            stt_context_options={
                "keyterm_detection": {"enabled": False},
                "forward_chat_context": False,
            },
            user_away_timeout=None,
        )
        runtime = Runtime(repo, saved, voice)
        agent = ControlledAgent(runtime)
        tasks = set()

        @voice.on("user_state_changed")
        def user_state(event):
            if event.new_state == "speaking":
                task = asyncio.create_task(runtime.speech_started())
                tasks.add(task)
                task.add_done_callback(tasks.discard)

        @voice.on("error")
        def error(event):
            runtime.launch_error(
                "Voice processing is unavailable. Your accepted answers are saved."
            )

        await voice.start(
            agent=agent,
            room=ctx.room,
            record=False,
            session_host=False,
            room_options=room_io.RoomOptions(
                participant_identity=saved.participant,
                text_input=False,
                text_output=False,
                video_input=False,
                audio_input=room_io.AudioInputOptions(
                    sample_rate=16000, num_channels=1, pre_connect_audio=False
                ),
                audio_output=room_io.AudioOutputOptions(sample_rate=24000),
            ),
        )
        await runtime.run()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as error:
        failure("room_job_unavailable", error)
    finally:
        if runtime:
            with suppress(Exception):
                await runtime.update(pause_lost_owner)
        if voice:
            await voice.aclose()
        await redis.aclose()


async def coordinate(repo, server, registered, stop):
    work = WorkCoordinator(repo, Gateway(repo.config))
    while not stop.is_set():
        try:
            # Pinned 1.8.2 compatibility seam: the public registration event plus connection flags
            # distinguish a registered live worker from a process with an open HTTP port.
            if registered.is_set() and not server._connecting and not server._connection_failed:
                await repo.redis.set("agent:registered", str(time.time()), ex=15)
            else:
                await repo.redis.delete("agent:registered")
            await work.cycle()
        except Exception:
            metric("coordinator_unavailable")
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), 3)
    with suppress(Exception):
        await repo.redis.delete("agent:registered")
    await work.close()


async def main():
    configure_logs()
    config = settings()
    server = AgentServer(
        ws_url=config.livekit_url,
        api_key=config.livekit_api_key.get_secret_value(),
        api_secret=config.livekit_api_secret.get_secret_value(),
        setup_fnc=prewarm,
        num_idle_processes=1,
        initialize_process_timeout=60,
        drain_timeout=15,
        shutdown_process_timeout=10,
        log_level="critical",
    )
    server.rtc_session(entrypoint, agent_name=config.livekit_agent_name)
    registered, stop = asyncio.Event(), asyncio.Event()
    server.on("worker_registered", lambda *_: registered.set())
    redis = Redis.from_url(
        config.redis_url.get_secret_value(),
        decode_responses=True,
        socket_timeout=3,
        socket_connect_timeout=3,
    )
    repo = Repository(redis, config)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    runner = asyncio.create_task(server.run(devmode=False))
    coordinator = asyncio.create_task(coordinate(repo, server, registered, stop))
    stopper = asyncio.create_task(stop.wait())
    try:
        await asyncio.wait((runner, stopper), return_when=asyncio.FIRST_COMPLETED)
    finally:
        stop.set()
        await coordinator
        await server.drain(timeout=15)
        await server.aclose()
        await runner
        stopper.cancel()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
