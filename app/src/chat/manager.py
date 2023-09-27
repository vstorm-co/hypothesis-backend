import logging

from starlette.websockets import WebSocket

from src.auth.schemas import UserDB
from src.chat.schemas import BroadcastData, ConnectMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user: UserDB, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user.email] = websocket
        logger.info("User %s connected to room %s", user.email, room_id)
        message = ConnectMessage(
            type="user_joined",
            user_email=user.email,
            sender_picture=user.picture,
            user_name=user.name,
        )
        for email, websocket in self.active_connections.get(room_id, {}).items():
            await websocket.send_json(message.model_dump())

    async def disconnect(self, websocket: WebSocket, user: UserDB, room_id: str):
        if (
            room_id in self.active_connections
            and user.email in self.active_connections[room_id]
        ):
            del self.active_connections[room_id][user.email]
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
            logger.info("User %s disconnected from room %s", user.email, room_id)
        message = ConnectMessage(
            type="user_left",
            user_email=user.email,
            sender_picture=user.picture,
            user_name=user.name,
        )
        for email, websocket in self.active_connections.get(room_id, {}).items():
            await websocket.send_json(message.model_dump())

    async def broadcast(self, broadcast: BroadcastData):
        if broadcast.room_id in self.active_connections:
            for user_email, connection in self.active_connections[
                broadcast.room_id
            ].items():
                await connection.send_json(
                    {
                        "type": broadcast.type,
                        "message": broadcast.message,
                        "sender_email": broadcast.sender_user_email,
                        "created_by": broadcast.created_by,
                        "sender_picture": broadcast.sender_picture,
                        "sender_name": broadcast.sender_name,
                    }
                )

    async def user_typing(self, user: UserDB, room_id: str):
        for email, websocket in self.active_connections.get(room_id, {}).items():
            if email == user.email:
                continue
            await websocket.send_json(
                {"type": "typing", "content": f"{user.name} is typing..."}
            )
