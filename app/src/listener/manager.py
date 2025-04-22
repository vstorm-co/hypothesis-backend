import asyncio
import json
import logging
from redis.exceptions import ConnectionError
from starlette.websockets import WebSocket
from src.auth.schemas import UserDB
from src.config import settings
from src.constants import Environment
from src.listener.constants import listener_room_name, room_changed_info
from src.listener.schemas import WSEventMessage
from src.redis_client import RedisPubSubManager

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.rooms: dict = {}
        self.pubsub_client = RedisPubSubManager()

    async def add_user_to_room(
        self, room_id: str, websocket: WebSocket, user: UserDB | None = None
    ) -> None:
        if settings.ENVIRONMENT == Environment.DEBUG:
            return

        # Notify all rooms about room state change
        await self.pubsub_client.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(type=room_changed_info, id=room_id).model_dump(mode="json")
            ),
        )

        if room_id not in self.rooms:
            self.rooms[room_id] = []

        # Ensure that user is not added twice
        for room_user, _ in self.rooms[room_id]:
            if user and room_user and room_user.email == user.email:
                return

        self.rooms[room_id].append((user, websocket))

        try:
            # Ensure the pubsub client is connected and subscribes to the room
            await self.pubsub_client.connect()
            await self._subscribe_to_room(room_id)
        except ConnectionError:
            logger.error("Failed to connect to Redis. Retrying...")
            await asyncio.sleep(1)
            await self.add_user_to_room(room_id, websocket, user)

    async def _subscribe_to_room(self, room_id: str):
        try:
            pubsub_subscriber = await self.pubsub_client.subscribe(room_id, self._pubsub_callback)
        except Exception as e:
            logger.error(f"Error subscribing to room {room_id}: {str(e)}")

    async def broadcast_to_room(self, room_id: str, message: str) -> None:
        await self.pubsub_client.publish(room_id, message)

    async def update_user_of_users_in_chat(self, room_id: str, user_db: UserDB) -> None:
        logger.info(f"User {user_db.email} joined room {room_id}")
        room_connections = self.rooms.get(room_id, [])
        for room_user, _ in room_connections:
            message = json.dumps({
                "type": "user_joined",
                "user_email": room_user.email,
                "sender_picture": room_user.picture,
                "user_name": room_user.name,
            })
            await self.broadcast_to_room(room_id, message)

    async def remove_user_from_room(
        self, room_id: str, websocket: WebSocket, user: UserDB | None = None
    ) -> None:
        if room_id in self.rooms:
            self.rooms[room_id] = [
                (room_user, ws) for room_user, ws in self.rooms[room_id] if ws != websocket
            ]
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                await self.pubsub_client.unsubscribe(room_id)

        if user:
            for room_user, _ in self.rooms.get(room_id, []):
                if room_user.email == user.email:
                    self.rooms[room_id] = [
                        (room_user, ws) for room_user, ws in self.rooms[room_id] if room_user.email != user.email
                    ]
                    break

            await self.pubsub_client.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(type=room_changed_info, id=room_id).model_dump(mode="json")
                ),
            )

            message = json.dumps({
                "type": "user_left",
                "user_email": user.email,
                "sender_picture": user.picture,
                "user_name": user.name,
            })
            await self.broadcast_to_room(room_id, message)

        try:
            await websocket.close()
        except Exception:
            pass

    async def _pubsub_callback(self, room_id: str, data: dict) -> None:
        room_connections = self.rooms.get(room_id, [])
        for room_user, socket in room_connections:
            try:
                if data.get("sender_user_email") == room_user.email:
                    continue
                await socket.send_json(data)
            except Exception:
                continue

    async def get_room_connections(self, room_id: str) -> list:
        return self.rooms.get(room_id, [])

    async def get_every_room_connections(self) -> dict:
        return self.rooms

ws_manager: WebSocketManager = WebSocketManager()
