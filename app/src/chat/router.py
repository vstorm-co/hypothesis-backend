from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.chat.schemas import Message

from . import service
from .config import ConnectionManager
from .utils import chat_with_chat

router = APIRouter()

manager = ConnectionManager()


@router.post("/room")
async def create_room(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    room = await service.create_room_in_db(jwt_data.user_id)
    return {"room": room}


@router.get("/room")
async def get_rooms(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    room = await service.get_room_from_db(jwt_data.user_id)
    return room


@router.get("/messages/")
async def get_messages(room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)):
    messages = await service.get_messages_from_db(room_id)
    print(messages)
    for msg in messages:
        print(f"Messages from for!: {msg}")
    return messages


@router.websocket("/ws/{room_id}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            content_to_db = Message(created_by="user", content=data, room_id=room_id)
            # print(data)
            await manager.send_personal_message(f"You wrote in chat: {data}", websocket)
            await manager.broadcast(f"Room #{room_id} says: {data}")
            await manager.broadcast(f"Chat answer: ")
            await service.create_message_in_db(content_to_db)
            bot_answer = ""
            async for message in chat_with_chat(data):
                bot_answer += message
                await manager.broadcast(f"{message}")
            bot_content = Message(created_by="bot", content=bot_answer, room_id=room_id)
            await service.create_message_in_db(bot_content)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Room #{room_id} left chat")
