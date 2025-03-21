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
        """
        Initializes the WebSocketManager.

        Attributes:
            rooms (dict): A dictionary to store WebSocket
            connections in different rooms.
            pubsub_client (RedisPubSubManager): An instance
            of the RedisPubSubManager class for pub-sub functionality.
        """
        self.rooms: dict = {}
        self.pubsub_client = RedisPubSubManager()

    async def add_user_to_room(
        self, room_id: str, websocket: WebSocket, user: UserDB | None = None
    ) -> None:
        """
        Adds a user's WebSocket connection to a room.

        Args:
            room_id (str): Room ID or channel name.
            websocket (WebSocket): WebSocket connection object.
            user (UserDB): User's database model.
        """
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
            # check if user is already in the room, no matter what the websocket is
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
            # Implement retry logic with a backoff strategy (e.g., exponential backoff)
            await asyncio.sleep(1)  # Simple delay for now
            # Retry connection attempt
            await self.add_user_to_room(room_id, websocket, user)  # Recursive call

    async def broadcast_to_room(self, room_id: str, message: str) -> None:
        """
        Broadcasts a message to all connected WebSockets in a room.

        Args:
            room_id (str): Room ID or channel name.
            message (str): Message to be broadcasted.
        """
        await self.pubsub_client.publish(room_id, message)

    async def update_user_of_users_in_chat(self, room_id: str, user_db: UserDB) -> None:
        """
        Informs all users in a room about a new user joining the room.

        Args:
            room_id (str): Room ID or channel name.
            user_db (UserDB): User's database model.
        """
        logger.info(f"User {user_db.email} joined room {room_id}")
        room_connections = self.rooms.get(room_id, [])
        for room_user, _ in room_connections:
            logger.info(f"Sending user joined message to {room_user.email}")
            message = json.dumps(
                {
                    "type": "user_joined",
                    "user_email": room_user.email,
                    "sender_picture": room_user.picture,
                    "user_name": room_user.name,
                }
            )
            await self.broadcast_to_room(room_id, message)

    async def remove_user_from_room(
        self, room_id: str, websocket: WebSocket, user: UserDB | None = None
    ) -> None:
        """
        Removes a user's WebSocket connection from a room.

        Args:
            room_id (str): Room ID or channel name.
            websocket (WebSocket): WebSocket connection object.
            user (UserDB): User's database model.
        """
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
            # delete user from self.rooom, find a user in tuple (user, websocket)
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
                await self.broadcast_to_room(room_id, message)

        try:
            await websocket.close()  # Ensure WebSocket is properly closed
        except Exception:
            pass

    async def _pubsub_data_reader(self, pubsub_subscriber):
        """
        Reads and broadcasts messages received from Redis PubSub.

        Args:
            pubsub_subscriber (aioredis.ChannelSubscribe): PubSub
            object for the subscribed channel.
        """
        while True:
            # message = await pubsub_subscriber.get_message(
            #     ignore_subscribe_messages=True
            # )
            # if message is None:
            #     continue
            try:
                message = await pubsub_subscriber.get_message(
                    ignore_subscribe_messages=True
                )
                if message is None:
                    continue
            except ConnectionError:
                logger.error("Failed to connect to Redis. Retrying...")
                # Implement retry logic with a backoff strategy
                # (e.g., exponential backoff)
                await asyncio.sleep(1)
                # Retry connection attempt
                await self._pubsub_data_reader(pubsub_subscriber)  # Recursive call

            room_id = message["channel"]
            raw_room_connections = self.rooms.get(room_id, [])
            # cleanup user duplication in room_connections by first tuple item in list[tuple]
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
                    if conn_user and sender_user_email == conn_user.email:
                        continue
                    await socket.send_json(data)
                except Exception:
                    continue

    async def get_room_connections(self, room_id: str) -> list:
        """
        Returns a list of WebSocket connections in a room.

        Args:
            room_id (str): Room ID or channel name.

        Returns:
            list: A list of WebSocket connections in the specified room.
        """
        return self.rooms.get(room_id, [])

    async def get_every_room_connections(self) -> dict:
        """
        Returns a dictionary of WebSocket connections in all rooms.

        Returns:
            dict: A dictionary of WebSocket connections in all rooms.
        """
        return self.rooms


ws_manager: WebSocketManager = WebSocketManager()
