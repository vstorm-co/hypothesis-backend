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
        self.active_connections: Dict[str, list[WebSocket]] = {}
        self.connection_user: Dict[WebSocket, Any] = {}
        self.chat_manager = ChatManager()

    async def connect(self, websocket: WebSocket, room_id: str, token: str = None):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info(f"WebSocket connected to room {room_id}")

        if token:
            user = get_user_from_token(token)
            if user:
                self.connection_user[websocket] = user
                logger.info(f"WebSocket associated with user {user.email}")

        asyncio.create_task(self._pubsub_data_reader(room_id))

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections and websocket in self.active_connections[room_id]:
            self.active_connections[room_id].remove(websocket)
            logger.info(f"WebSocket disconnected from room {room_id}")
        if websocket in self.connection_user:
            del self.connection_user[websocket]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, room_id: str, message: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(message)

    async def _pubsub_data_reader(self, room_id: str):
        channel = redis_client.pubsub()
        await channel.subscribe(f"listener_{room_id}")

        logger.info(f"Listening to Redis channel: listener_{room_id}")

        async for message in channel.listen():
            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                await self._on_redis_message(room_id, data)
            except Exception as e:
                logger.error(f"Error handling Redis message: {e}")

    async def _on_redis_message(self, room_id: str, data: Dict[str, Any]):
        sender_user_email = data.get("sender_user_email")

        if room_id not in self.active_connections:
            return

        for connection in self.active_connections[room_id]:
            conn_user = self.connection_user.get(connection)
            if sender_user_email is not None and conn_user and sender_user_email == conn_user.email:
                continue

            try:
                await connection.send_text(json.dumps(data))
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")


ws_manager: WebSocketManager = WebSocketManager()
