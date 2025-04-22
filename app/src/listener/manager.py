import asyncio
import json
import logging

from fastapi import WebSocket
from redis.exceptions import ConnectionError

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

    async def connect(self, websocket: WebSocket, room_id: str, user: UserDB = None):
        await websocket.accept()

        if user:
            logger.info(f"WebSocket associated with user {user.email}")

        await self.add_user_to_room(room_id, websocket, user)

    async def add_user_to_room(
        self, room_id: str, websocket: WebSocket, user: UserDB | None = None
    ) -> None:
        if settings.ENVIRONMENT == Environment.DEBUG:
            return

        await self.pubsub_client.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(
                    type=room_changed_info,
                    id=room_id,
                ).model_dump(mode="json")
            ),
        )

        if room_id in self.rooms:
            for room_user, _ in self.rooms[room_id]:
                if user and room_user and room_user.email == user.email:
                    return
            self.rooms[room_id].append((user, websocket))
            return

        self.rooms[room_id] = [(user, websocket)]

        try:
            await self.pubsub_client.connect()
            pubsub_subscriber = await self.pubsub_client.subscribe(room_id)
            asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber))
        except ConnectionError:
            logger.error("Failed to connect to Redis. Retrying...")
            await asyncio.sleep(1)
            await self.add_user_to_room(room_id, websocket, user)

    async def broadcast(self, room_id: str, message: str):
        await self.pubsub_client.publish(room_id, message)

    async def _pubsub_data_reader(self, pubsub_subscriber):
        while True:
            try:
                message = await pubsub_subscriber.get_message(
                    ignore_subscribe_messages=True
                )
                if message is None:
                    continue
            except ConnectionError:
                logger.error("Failed to connect to Redis. Retrying...")
                await asyncio.sleep(1)
                await self._pubsub_data_reader(pubsub_subscriber)

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

            for conn_user, socket in room_connections:
                data = message["data"]
                data = json.loads(data)
                sender_user_email = data.get("sender_user_email", None)
                try:
                    if conn_user and sender_user_email == conn_user.email:
                        continue
                    await socket.send_json(data)
                except Exception:
                    continue

    async def disconnect(self, websocket: WebSocket, room_id: str, user: UserDB | None = None):
        if self.rooms.get(room_id):
            self.rooms[room_id] = [
                room_data_tuple
                for room_data_tuple in self.rooms[room_id]
                if isinstance(room_data_tuple, tuple)
                and room_data_tuple[1] != websocket
            ]

            if not self.rooms[room_id]:
                del self.rooms[room_id]
                await self.pubsub_client.unsubscribe(room_id)

        if self.pubsub_client.celery_connection and not self.rooms.get(room_id):
            self.pubsub_client.celery_connection = False
            await self.pubsub_client.unsubscribe(room_id)

        if user:
            for room_user, _ in self.rooms.get(room_id, []):
                if room_user.email == user.email:
                    self.rooms[room_id] = [
                        room_data_tuple
                        for room_data_tuple in self.rooms[room_id]
                        if room_data_tuple[0].email != user.email
                    ]
                    break

            await self.pubsub_client.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(
                        type=room_changed_info,
                        id=room_id,
                    ).model_dump(mode="json")
                ),
            )

            room_connections = self.rooms.get(room_id, [])
            for room_user, _ in room_connections:
                message = json.dumps(
                    {
                        "type": "user_left",
                        "user_email": user.email,
                        "sender_picture": user.picture,
                        "user_name": user.name,
                    }
                )
                await self.broadcast(room_id, message)

        try:
            await websocket.close()
        except Exception:
            pass

    async def get_room_connections(self, room_id: str):
        return self.rooms.get(room_id, [])

    async def get_all_connections(self):
        return self.rooms

ws_manager: WebSocketManager = WebSocketManager()
