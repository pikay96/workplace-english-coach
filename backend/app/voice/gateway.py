import asyncio
import json
from datetime import timedelta

from livekit import api

from app.config import Settings
from app.sessions.models import Session


class Gateway:
    def __init__(self, config: Settings):
        self.config = config

    def client(self):
        return api.LiveKitAPI(
            url=self.config.livekit_url,
            api_key=self.config.livekit_api_key.get_secret_value(),
            api_secret=self.config.livekit_api_secret.get_secret_value(),
            timeout=__import__("aiohttp").ClientTimeout(total=10),
        )

    async def remove_room(self, room: str):
        async with self.client() as client:
            try:
                await client.room.delete_room(api.DeleteRoomRequest(room=room))
            except api.TwirpError as error:
                if error.code != "not_found":
                    raise

    async def dispatch(self, session: Session):
        async with asyncio.timeout(10), self.client() as client:
            await client.room.create_room(
                api.CreateRoomRequest(
                    name=session.room, empty_timeout=60, departure_timeout=20, max_participants=2
                )
            )
            await client.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    room=session.room,
                    agent_name=self.config.livekit_agent_name,
                    metadata=json.dumps(
                        {
                            "session_id": session.id,
                            "guest_id": session.guest_id,
                            "connection_epoch": session.connection_epoch,
                        }
                    ),
                )
            )

    def token(self, session: Session) -> str:
        return (
            api.AccessToken(
                self.config.livekit_api_key.get_secret_value(),
                self.config.livekit_api_secret.get_secret_value(),
            )
            .with_identity(session.participant)
            .with_ttl(timedelta(minutes=5))
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=session.room,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=False,
                    can_publish_sources=["microphone"],
                )
            )
            .to_jwt()
        )
