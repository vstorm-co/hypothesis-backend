import logging

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_email: str, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_email] = websocket
        logger.info("User %s connected to room %s", user_email, room_id)

    def disconnect(self, websocket: WebSocket, user_email: str, room_id: str):
        if (
            room_id in self.active_connections
            and user_email in self.active_connections[room_id]
        ):
            del self.active_connections[room_id][user_email]
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
            logger.info("User %s disconnected from room %s", user_email, room_id)

    async def broadcast(
        self,
        message: str,
        room_id: str,
        sender_user_mail: str,
        created_by: str = "user",
        sender_picture: str | None = None,
        sender_name: str | None = None,
    ):
        if room_id in self.active_connections:
            for user_email, connection in self.active_connections[room_id].items():
                await connection.send_json(
                    {
                        "message": message,
                        "sender_email": sender_user_mail,
                        "created_by": created_by,
                        "sender_picture": sender_picture,
                        "sender_name": sender_name,
                    }
                )
