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

    async def _pubsub_data_reader(self, pubsub_subscriber):
        """
        Reads and broadcasts messages received from Redis PubSub.

        Args:
            pubsub_subscriber (aioredis.ChannelSubscribe): PubSub
            object for the subscribed channel.
        """
        while True:
            try:
                message = await pubsub_subscriber.get_message(
                    ignore_subscribe_messages=True
                )
                if message is None:
                    continue

                room_id = message["channel"]
                raw_room_connections = self.rooms.get(room_id, [])

                # Cleanup user duplication in room_connections
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
                    conn_user: UserDB | None
                    socket: WebSocket
                    conn_user, socket = connection
                    data = message["data"]
                    data = json.loads(data)

                    sender_user_email = data.get("sender_user_email", None)

                    try:
                        # Only send if the user is not the sender of the message
                        if conn_user and sender_user_email == conn_user.email:
                            continue
                        await socket.send_json(data)
                    except Exception as e:
                        logger.error(f"Error sending message: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error in pubsub data reader: {e}")
                await asyncio.sleep(1)  # Retry with delay in case of error

    async def add_user_to_room(self, room_id: str, websocket: WebSocket, user: UserDB | None = None) -> None:
        if settings.ENVIRONMENT == Environment.DEBUG:
            return

        if room_id in self.rooms:
            for room_user, _ in self.rooms[room_id]:
                if user and room_user and room_user.email == user.email:
                    return
            self.rooms[room_id].append((user, websocket))
        else:
            self.rooms[room_id] = [(user, websocket)]

        try:
            await self.pubsub_client.connect()  # Ensure connection is made
            pubsub_subscriber = await self.pubsub_client.subscribe(room_id, self._pubsub_callback)
            asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber))
        except ConnectionError:
            logger.error("Failed to connect to Redis. Retrying...")
            await asyncio.sleep(1)  # Retry logic for connection
            await self.add_user_to_room(room_id, websocket, user)  # Retry add user

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
