from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.auth.service import get_user_by_id
from src.chat import service
from src.chat.config import ConnectionManager
from src.chat.exceptions import RoomAlreadyExists, RoomDoesNotExist, RoomIsNotShared, NotTheSameOrganizations
from src.chat.schemas import (
    MessageDB,
    MessageDetails,
    RoomCreateInput,
    RoomCreateInputDetails,
    RoomDB,
    RoomDeleteOutput,
    RoomDetails,
    RoomUpdate,
    RoomUpdateInputDetails,
)
from src.chat.utils import chat_with_chat

router = APIRouter()

manager = ConnectionManager()


@router.get("/rooms", response_model=list[RoomDB])
async def get_rooms(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    rooms = await service.get_rooms_from_db(jwt_data.user_id)

    if not rooms:
        return []

    return [RoomDB(**dict(room)) for room in rooms]


@router.post("/room", response_model=RoomDB)
async def create_room(
    room_data: RoomCreateInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    room_input_data = RoomCreateInputDetails(
        **room_data.model_dump(), user_id=jwt_data.user_id
    )
    room = await service.create_room_in_db(room_input_data)

    if not room:
        raise RoomAlreadyExists()

    return RoomDB(**dict(room))


# create post method for room
@router.patch("/room/{room_id}", response_model=RoomDB)
async def update_room(
    room_id: str,
    room_data: RoomUpdate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    room_update_details = RoomUpdateInputDetails(
        **room_data.model_dump(exclude_unset=True),
        room_id=room_id,
        user_id=jwt_data.user_id,
    )
    room = await service.update_room_in_db(room_update_details)

    if not room:
        raise RoomDoesNotExist()

    return RoomDB(**dict(room))


@router.delete("/room/{room_id}", response_model=RoomDeleteOutput)
async def delete_room(
    room_id: str,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    await service.delete_room_from_db(room_id, jwt_data.user_id)

    return RoomDeleteOutput(status="success")


@router.get("/room/{room_id}", response_model=RoomDetails)
async def get_room_with_messages(
    room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    room = await service.get_room_by_id_from_db(room_id, jwt_data.user_id)
    messages = await service.get_messages_from_db(room_id)

    if not room:
        raise RoomDoesNotExist()

    if not room['share']:
        raise RoomIsNotShared()

    user = await get_user_by_id(jwt_data.user_id)
    room_user = await get_user_by_id(room['user_id'])

    if user['organization_uuid'] is not None and user['organization_uuid'] != room_user['organization_uuid']:
        raise NotTheSameOrganizations()

    room_schema = RoomDB(**dict(room))
    messages_schema = [MessageDB(**dict(message)) for message in messages]

    return RoomDetails(
        uuid=str(room_schema.uuid), name=room_schema.name, messages=messages_schema
    )


@router.get("/messages/", response_model=list[MessageDB])
async def get_messages(room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)):
    messages = await service.get_messages_from_db(room_id)

    return [MessageDB(**dict(message)) for message in messages]


@router.websocket("/ws/{room_id}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            content_to_db = MessageDetails(
                created_by="user", content=data, room_id=room_id
            )
            await service.create_message_in_db(content_to_db)
            bot_answer = ""
            async for message in chat_with_chat(data):
                bot_answer += message
                await manager.broadcast(f"{message}")
            bot_content = MessageDetails(
                created_by="bot", content=bot_answer, room_id=room_id
            )
            await service.create_message_in_db(bot_content)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
