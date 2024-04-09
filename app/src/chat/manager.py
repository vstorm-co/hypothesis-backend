import logging
from typing import Dict, List, Tuple

from pydantic import EmailStr
from starlette.websockets import WebSocket
from websockets.exceptions import ConnectionClosedOK

from src.active_room_users.service import (
    create_active_room_user_in_db,
    delete_active_room_user_from_db,
)
from src.auth.schemas import UserDB
from src.auth.service import get_user_by_email
from src.chat.schemas import (
    APIInfoBroadcastData,
    BroadcastData,
    ConnectMessage,
    GlobalConnectMessage,
)
from src.listener.constants import room_changed_info
from src.listener.manager import listener as global_listener
from src.listener.schemas import WSEventMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[Tuple[EmailStr, WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, user: UserDB, room_id: str):
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append((user.email, websocket))
        logger.info("User %s connected to room %s", user.email, room_id)

        await create_active_room_user_in_db(room_id, user.id)

        await self._inform_other_users_of_connecting(user, room_id, websocket)
        await global_listener.receive_and_publish_message(
            WSEventMessage(
                type=room_changed_info,
                id=room_id,
            ).model_dump(mode="json")
        )

    async def _inform_other_users_of_connecting(
        self, user: UserDB, room_id: str, wb: WebSocket
    ):
        user_connected_message = ConnectMessage(
            type="user_joined",
            user_email=user.email,
            sender_picture=user.picture,
            user_name=user.name,
        )
        global_connect_message = GlobalConnectMessage(
            **dict(user_connected_message), room_id=room_id
        )
        await global_listener.add_user_to_room(global_connect_message)
        await global_listener.receive_and_publish_message(
            global_connect_message.model_dump(mode="json")
        )
        logger.info("GLOBAL WS: User %s connected to room %s", user.email, room_id)

        for email, websocket in self.active_connections[room_id]:
            try:
                await websocket.send_json(
                    user_connected_message.model_dump(mode="json")
                )
            except ConnectionClosedOK:
                logger.error("Connection of websocket is closed")
            except RuntimeError:
                logger.error("Runtime error")

            # inform about other users in chat
            email_user = await get_user_by_email(email)
            if not email_user:
                continue
            user_db = UserDB(**dict(email_user))
            connect_info = ConnectMessage(
                type="user_joined",
                user_email=user_db.email,
                sender_picture=user_db.picture,
                user_name=user_db.name,
            )
            try:
                await wb.send_json(connect_info.model_dump(mode="json"))
            except ConnectionClosedOK:
                logger.error("Connection of websocket is closed")
            except RuntimeError:
                logger.error("Runtime error")

            logger.info(
                "WS ROOM_ID(%s): User %s connected to room %s",
                room_id,
                user_db.email,
                room_id,
            )

    async def disconnect(self, user: UserDB, room_id: str):
        if room_id not in self.active_connections:
            return

        self.active_connections[room_id] = [
            (email, websocket)
            for email, websocket in self.active_connections[room_id]
            if email != user.email
        ]

        message = ConnectMessage(
            type="user_left",
            user_email=user.email,
            sender_picture=user.picture,
            user_name=user.name,
        )
        global_message = GlobalConnectMessage(**message.model_dump(), room_id=room_id)
        await global_listener.receive_and_publish_message(
            global_message.model_dump(mode="json")
        )
        await global_listener.remove_user_from_room(global_message)

        await delete_active_room_user_from_db(room_id, user.id)

        for email, websocket in self.active_connections[room_id]:
            await websocket.send_json(message.model_dump())

    async def broadcast(self, data: BroadcastData):
        if data.room_id not in self.active_connections:
            return

        for email, websocket in self.active_connections[data.room_id]:
            try:
                await websocket.send_json(
                    {
                        "type": data.type,
                        "message": data.message,
                        "sender_email": data.sender_user_email,
                        "created_by": data.created_by,
                        "sender_picture": data.sender_picture,
                        "sender_name": data.sender_name,
                    }
                )
            except ConnectionClosedOK:
                logger.error("Connection of websocket is closed")
            except RuntimeError:
                logger.error("Runtime error")

    async def broadcast_api_info(self, data: APIInfoBroadcastData):
        if data.room_id not in self.active_connections:
            return

        for email, websocket in self.active_connections[data.room_id]:
            try:
                await websocket.send_json(
                    data.model_dump(exclude={"room_id"}, mode="json")
                )
            except ConnectionClosedOK:
                logger.error("Connection of websocket is closed")

    async def user_typing(self, user: UserDB, room_id: str):
        if room_id not in self.active_connections:
            return

        for email, websocket in self.active_connections[room_id]:
            if email == user.email:
                continue
            await websocket.send_json({"type": "typing", "content": f"{user.name}"})


def get_connection_manager():
    return ConnectionManager()


manager = get_connection_manager()
