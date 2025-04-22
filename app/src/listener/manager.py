import asyncio
import json
import logging
from typing import Dict, List, Tuple, Optional, Set

from redis.exceptions import ConnectionError
from starlette.websockets import WebSocket

from src.auth.schemas import UserDB
from src.config import settings
from src.constants import Environment
from src.listener.constants import listener_room_name, room_changed_info
from src.listener.schemas import WSEventMessage
from src.redis_client import RedisPubSubManager, pub_sub_manager, RedisData, set_redis_key, get_by_key

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        """
        Initializes the WebSocketManager.
        """
        self.pubsub_client = RedisPubSubManager()
        self._connected = False
        self.websockets = {}

    async def _ensure_connection(self):
        """Ensures Redis connection is established."""
        if not self._connected:
            try:
                await self.pubsub_client.connect()
                self._connected = True
            except ConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connected = False
                raise

    async def add_user_to_room(
            self, room_id: str, websocket: WebSocket, user: Optional[UserDB] = None
    ) -> None:
        """
        Adds a user's WebSocket connection to a room (Redis-backed).

        Args:
            room_id (str): Room ID or channel name.
            websocket (WebSocket): WebSocket connection object.
            user (UserDB, optional): User's database model.
        """
        if settings.ENVIRONMENT == Environment.DEBUG:
            return

        try:
            await self._ensure_connection()

            # Notify about room change
            await pub_sub_manager.publish(
                listener_room_name,
                WSEventMessage(
                    type=room_changed_info,
                    id=room_id,
                ).model_dump(mode="json")
            )

            # Redis key for room members
            redis_key = f"room:{room_id}:members"
            # Add user to Redis room members set
            if user:
                # Check if user already present
                existing = await get_by_key(redis_key)
                members = set(json.loads(existing) if existing else [])
                if user.email in members:
                    return
                members.add(user.email)
                await set_redis_key(RedisData(key=redis_key, value=json.dumps(list(members)), ttl=None))
            
            # Subscribe to room events with a callback if not already
            async def room_callback(room_id, data):
                # You may want to forward data to all sockets in this room
                pass  # Implement as needed
            await pub_sub_manager.subscribe(room_id, room_callback)

            # Optionally, maintain a local mapping of websockets for FastAPI
            if room_id not in self.websockets:
                self.websockets[room_id] = []
            self.websockets[room_id].append((user, websocket))

        except Exception as e:
            logger.error(f"Error adding user to room: {e}")
            raise

    async def broadcast_to_room(self, room_id: str, message: str) -> None:
        """
        Broadcasts a message to all connected WebSockets in a room.

        Args:
            room_id (str): Room ID or channel name.
            message (str): Message to be broadcasted.
        """
        try:
            await self._ensure_connection()
            await pub_sub_manager.publish(room_id, message)
        except ConnectionError:
            logger.error("Failed to connect to Redis. Retrying...")
            await asyncio.sleep(1)  # Simple delay before retry
            await self.broadcast_to_room(room_id, message)  # Retry

    async def update_user_of_users_in_chat(self, room_id: str, user_db: UserDB) -> None:
        """
        Informs all users in a room about a new user joining the room.

        Args:
            room_id (str): Room ID or channel name.
            user_db (UserDB): User's database model.
        """
        logger.info(f"User {user_db.email} joined room {room_id}")
        room_connections = self.websockets.get(room_id, [])
        for room_user, _ in room_connections:
            logger.info(f"Sending user joined message to {room_user.email}")
            message = json.dumps({
                "type": "user_joined",
                "user_email": room_user.email,
                "sender_picture": room_user.picture,
                "user_name": room_user.name,
            })
            await self.broadcast_to_room(room_id, message)

    async def remove_user_from_room(
            self, room_id: str, websocket: WebSocket, user: Optional[UserDB] = None
    ) -> None:
        """
        Removes a user's WebSocket connection from a room.

        Args:
            room_id (str): Room ID or channel name.
            websocket (WebSocket): WebSocket connection object.
            user (UserDB, optional): User's database model.
        """
        try:
            await self._ensure_connection()

            if room_id in self.websockets:
                # Remove the WebSocket connection from the room
                self.websockets[room_id] = [
                    conn for conn in self.websockets[room_id] if conn[1] != websocket
                ]

                # If the room is now empty, remove it from the rooms dictionary
                if not self.websockets[room_id]:
                    del self.websockets[room_id]

            # Notify about room change
            await pub_sub_manager.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(
                        type=room_changed_info,
                        id=room_id,
                    ).model_dump(mode="json")
                ),
            )

            # Notify other users about the user leaving the room
            if user:
                for room_user, _ in self.websockets.get(room_id, []):
                    if room_user and room_user.email == user.email:
                        message = json.dumps({
                            "type": "user_left",
                            "user_email": user.email,
                            "sender_picture": user.picture,
                            "user_name": user.name,
                        })
                        await self.broadcast_to_room(room_id, message)
                        break
        except ConnectionError:
            logger.error("Failed to connect to Redis. Retrying...")
            await asyncio.sleep(1)  # Simple delay before retry
            await self.remove_user_from_room(room_id, websocket, user)  # Retry

    async def _pubsub_data_reader(self, pubsub_subscriber, room_id):
        """
        Reads and broadcasts messages received from Redis PubSub.

        Args:
            pubsub_subscriber (aioredis.ChannelSubscribe): PubSub object for the subscribed channel.
            room_id (str): Room ID or channel name.
        """
        while True:
            try:
                message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
                if message is None:
                    await asyncio.sleep(0.01)
                    continue

                data = json.loads(message["data"])
                sender_user_email = data.get("sender_user_email", None)

                for connection in self.websockets.get(room_id, []):
                    conn_user, socket = connection
                    if conn_user and sender_user_email == conn_user.email:
                        continue
                    try:
                        await socket.send_json(data)
                    except Exception:
                        continue
            except ConnectionError:
                logger.error("Failed to connect to Redis. Retrying...")
                await asyncio.sleep(1)  # Simple delay before retry
                await self._pubsub_data_reader(pubsub_subscriber, room_id)  # Retry

    async def get_room_connections(self, room_id: str) -> List[Tuple[Optional[UserDB], WebSocket]]:
        """
        Returns a list of WebSocket connections in a room.

        Args:
            room_id (str): Room ID or channel name.

        Returns:
            list: A list of WebSocket connections in the specified room.
        """
        return self.websockets.get(room_id, [])

    async def get_every_room_connections(self) -> Dict[str, List[Tuple[Optional[UserDB], WebSocket]]]:
        """
        Returns a dictionary of WebSocket connections in all rooms.

        Returns:
            dict: A dictionary of WebSocket connections in all rooms.
        """
        return self.websockets

ws_manager: WebSocketManager = WebSocketManager()
