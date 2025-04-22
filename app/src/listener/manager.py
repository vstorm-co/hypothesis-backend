# websocket_manager.py

import asyncio
import json
import logging

from starlette.websockets import WebSocket
from src.auth.schemas import UserDB
from src.config import settings, Environment
from src.listener.constants import listener_room_name, room_changed_info
from src.listener.schemas import WSEventMessage
from src.redis_client import RedisPubSubManager

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.rooms: dict[str, list[tuple[UserDB | None, WebSocket]]] = {}
        self.pubsub_client = RedisPubSubManager()

    async def add_user_to_room(self, room_id: str, websocket: WebSocket, user: UserDB | None = None):
        if settings.ENVIRONMENT == Environment.DEBUG:
            return

        if room_id not in self.rooms:
            self.rooms[room_id] = []
            await self.pubsub_client.subscribe(room_id, self._message_callback)

        for room_user, _ in self.rooms[room_id]:
            if user and room_user and room_user.email == user.email:
                return

        self.rooms[room_id].append((user, websocket))

        await self.pubsub_client.publish(listener_room_name,
                                         WSEventMessage(type=room_changed_info, id=room_id).model_dump(mode="json"))

    async def remove_user_from_room(self, room_id: str, websocket: WebSocket, user: UserDB | None = None):
        if room_id in self.rooms:
            self.rooms[room_id] = [tup for tup in self.rooms[room_id] if tup[1] != websocket]
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                await self.pubsub_client.unsubscribe(room_id)

        if user:
            await self.pubsub_client.publish(listener_room_name,
                                             WSEventMessage(type=room_changed_info, id=room_id).model_dump(mode="json"))
            for room_user, _ in self.rooms.get(room_id, []):
                message = {
                    "type": "user_left",
                    "user_email": user.email,
                    "sender_picture": user.picture,
                    "user_name": user.name,
                }
                await self.pubsub_client.publish(room_id, message)

        try:
            await websocket.close()
        except Exception:
            pass

    async def broadcast_to_room(self, room_id: str, message: dict):
        await self.pubsub_client.publish(room_id, message)

    async def update_user_of_users_in_chat(self, room_id: str, user_db: UserDB):
        logger.info(f"User {user_db.email} joined room {room_id}")
        for room_user, _ in self.rooms.get(room_id, []):
            logger.info(f"Sending user joined message to {room_user.email}")
            message = {
                "type": "user_joined",
                "user_email": user_db.email,
                "sender_picture": user_db.picture,
                "user_name": user_db.name,
            }
            await self.broadcast_to_room(room_id, message)

    async def _message_callback(self, room_id: str, message: dict):
        for user, websocket in self.rooms.get(room_id, []):
            if not user or message.get("sender_user_email") == user.email:
                continue
            try:
                await websocket.send_json(message)
            except Exception:
                logger.warning("Failed to send WebSocket message to %s", user.email if user else "anonymous")

    async def get_room_connections(self, room_id: str) -> list:
        return self.rooms.get(room_id, [])

    async def get_every_room_connections(self) -> dict:
        return self.rooms


ws_manager: WebSocketManager = WebSocketManager()
