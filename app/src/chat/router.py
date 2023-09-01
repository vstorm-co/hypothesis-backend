from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.chat.schemas import (
    Message,
    RoomCreate,
    RoomCreateWithUserId,
    RoomUpdate,
    RoomUpdateWithId,
)

from . import service
from .config import ConnectionManager
from .utils import chat_with_chat

router = APIRouter()

manager = ConnectionManager()


@router.post("/room")
async def create_room(
    room_data: RoomCreate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    room_data = RoomCreateWithUserId(**room_data.model_dump(), user_id=jwt_data.user_id)
    room = await service.create_room_in_db(room_data)
    return {"room": room}


# create post method for room
@router.put("/room/{room_id}")
async def update_room(
    room_id: str,
    room_data: RoomUpdate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    room_data_with_id = RoomUpdateWithId(**room_data.model_dump(), room_id=room_id)
    room = await service.update_room_in_db(room_data_with_id)
    return room


@router.delete("/room/{room_id}")
async def delete_room(
    room_id: str,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    await service.delete_room_from_db(room_id, jwt_data.user_id)
    return {"status": "ok"}


@router.get("/room")
async def get_rooms(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    room = await service.get_rooms_from_db(jwt_data.user_id)
    return room


@router.get("/messages/")
async def get_messages(room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)):
    messages = await service.get_messages_from_db(room_id)

    return messages


@router.websocket("/ws/{room_id}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            content_to_db = Message(created_by="user", content=data, room_id=room_id)
            await service.create_message_in_db(content_to_db)
            bot_answer = ""
            async for message in chat_with_chat(data):
                bot_answer += message
                await manager.broadcast(f"{message}")
            bot_content = Message(created_by="bot", content=bot_answer, room_id=room_id)
            await service.create_message_in_db(bot_content)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
