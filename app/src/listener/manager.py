import asyncio
import json
import logging

from redis.exceptions import ConnectionError
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
        self.listener_room_subscribed = False

    async def add_user_to_room(self, room_id: str, websocket: WebSocket, user: UserDB | None = None):
        if settings.ENVIRONMENT == Environment.DEBUG:
            return

        if room_id not in self.rooms:
            self.rooms[room_id] = []

            try:
                await self.pubsub_client.connect()
                pubsub_subscriber = await self.pubsub_client.subscribe(room_id)
                asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber))

                # Ensure listener_room_name is subscribed once
                if not self.listener_room_subscribed:
                    listener_subscriber = await self.pubsub_client.subscribe(listener_room_name)
                    asyncio.create_task(self._pubsub_data_reader(listener_subscriber))
                    self.listener_room_subscribed = True

            except ConnectionError:
                logger.error("Failed to connect to Redis. Retrying...")
                await asyncio.sleep(1)
                await self.add_user_to_room(room_id, websocket, user)
                return

        for room_user, _ in self.rooms[room_id]:
            if user and room_user and room_user.email == user.email:
                return

        self.rooms[room_id].append((user, websocket))

        await self.pubsub_client.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(type=room_changed_info, id=room_id).model_dump(mode="json")
            ),
        )

    async def remove_user_from_room(self, room_id: str, websocket: WebSocket, user: UserDB | None = None):
        if room_id in self.rooms:
            self.rooms[room_id] = [tup for tup in self.rooms[room_id] if tup[1] != websocket]
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                await self.pubsub_client.unsubscribe(room_id)

        if user:
            await self.pubsub_client.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(type=room_changed_info, id=room_id).model_dump(mode="json")
                ),
            )
            for room_user, _ in self.rooms.get(room_id, []):
                message = json.dumps({
                    "type": "user_left",
                    "user_email": user.email,
                    "sender_picture": user.picture,
                    "user_name": user.name,
                })
                await self.pubsub_client.publish(room_id, message)

        try:
            await websocket.close()
        except Exception:
            pass

    async def broadcast_to_room(self, room_id: str, message: str):
        await self.pubsub_client.publish(room_id, message)

    async def update_user_of_users_in_chat(self, room_id: str, user_db: UserDB):
        logger.info(f"User {user_db.email} joined room {room_id}")
        for room_user, _ in self.rooms.get(room_id, []):
            logger.info(f"Sending user joined message to {room_user.email}")
            message = json.dumps({
                "type": "user_joined",
                "user_email": user_db.email,
                "sender_picture": user_db.picture,
                "user_name": user_db.name,
            })
            await self.broadcast_to_room(room_id, message)

    async def _pubsub_data_reader(self, pubsub_subscriber):
        while True:
            try:
                message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
                if message is None:
                    await asyncio.sleep(0.01)
                    continue
            except ConnectionError:
                logger.error("Failed to read from Redis pubsub. Retrying...")
                await asyncio.sleep(1)
                continue

            room_id = message["channel"]
            raw_room_connections = self.rooms.get(room_id, [])
            room_connections_set = set()
            room_connections = []

            for conn_data in raw_room_connections:
                user_db = conn_data[0]
                if not isinstance(user_db, UserDB):
                    continue
                if user_db.email in room_connections_set:
                    continue
                room_connections_set.add(user_db.email)
                room_connections.append(conn_data)

            if room_id == listener_room_name:
                room_connections = raw_room_connections

            for connection in room_connections:
                conn_user, socket = connection
                data = message["data"]
                data = json.loads(data)
                sender_user_email = data.get("sender_user_email")

                try:
                    if conn_user and sender_user_email == conn_user.email:
                        continue
                    await socket.send_json(data)
                except Exception:
                    continue

    async def get_room_connections(self, room_id: str) -> list:
        return self.rooms.get(room_id, [])

    async def get_every_room_connections(self) -> dict:
        return self.rooms


ws_manager: WebSocketManager = WebSocketManager()
