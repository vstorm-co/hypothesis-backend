from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials

from src.auth.exceptions import UserNotFound
from src.auth.jwt import parse_jwt_user_data, parse_jwt_user_data_optional
from src.auth.schemas import JWTData, UserDB
from src.auth.service import get_user_by_id
from src.chat import service
from src.chat.exceptions import RoomAlreadyExists, RoomDoesNotExist
from src.chat.manager import ConnectionManager
from src.chat.schemas import (
    BroadcastData,
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
from src.chat.validators import is_room_private, in_the_same_org

router = APIRouter()

manager = ConnectionManager()


@router.get("/rooms", response_model=list[RoomDB])
async def get_rooms(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    rooms = await service.get_rooms_from_db(jwt_data.user_id)

    if not rooms:
        return []

    return [RoomDB(**dict(room)) for room in rooms]


@router.get("/room/{room_id}", response_model=RoomDetails)
async def get_room_with_messages(
    room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    room = await service.get_room_by_id_from_db(room_id)
    if not room:
        raise RoomDoesNotExist()
    # create room schema
    room_schema = RoomDB(**dict(room))

    # check if user has access to room
    user = await get_user_by_id(jwt_data.user_id)
    room_owner_user = await get_user_by_id(room_schema.user_id)
    if not user or not room_owner_user:
        raise UserNotFound()
    user_schema = UserDB(**dict(user))

    # check if room is private
    if is_room_private(room_schema, user_schema.id):
        raise RoomDoesNotExist()

    # check if room is shared for Organization
    if not await in_the_same_org(room_schema, user_schema.id):
        raise RoomDoesNotExist()

    # get messages
    messages = await service.get_messages_from_db(room_id)
    messages_schema = [MessageDB(**dict(message)) for message in messages]

    return RoomDetails(
        uuid=str(room_schema.uuid),
        name=room_schema.name,
        owner=room_schema.user_id,
        visibility=room_schema.visibility,
        share=room_schema.share,
        messages=messages_schema,
    )


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
        **room_data.model_dump(),
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


@router.get("/messages/", response_model=list[MessageDB])
async def get_messages(room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)):
    messages = await service.get_messages_from_db(room_id)

    return [MessageDB(**dict(message)) for message in messages]


@router.websocket("/ws/{room_id}/{token}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: str, token: str):
    # check if user is authenticated
    jwt_data: JWTData | None = await parse_jwt_user_data_optional(
        HTTPAuthorizationCredentials(scheme="bearer", credentials=token)
    )
    if not jwt_data:
        raise UserNotFound()
    user = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise UserNotFound()
    user_db = UserDB(**dict(user))

    await manager.connect(
        websocket=websocket, room_id=room_id, user_email=user_db.email
    )
    try:
        while True:
            # get user message
            data = await websocket.receive_text()
            user_broadcast_data = BroadcastData(
                message=data,
                room_id=room_id,
                sender_user_email=user_db.email,
                created_by="user",
                sender_name=user_db.name,
                sender_picture=user_db.picture,
            )
            # broadcast message to all users in room
            await manager.broadcast(user_broadcast_data)
            # create user message in db
            content_to_db = MessageDetails(
                created_by="user",
                content=data,
                room_id=room_id,
                user_id=user_db.id,
            )
            await service.create_message_in_db(content_to_db)

            # chat with chatbot
            bot_answer = ""
            async for message in chat_with_chat(data):
                bot_answer += message
                bot_broadcast_data = BroadcastData(
                    message=message,
                    room_id=room_id,
                    sender_user_email=user_db.email,
                    created_by="bot",
                )
                await manager.broadcast(bot_broadcast_data)

            # create bot message in db
            bot_content = MessageDetails(
                created_by="bot",
                content=bot_answer,
                room_id=room_id,
                user_id=user_db.id,
            )
            await service.create_message_in_db(bot_content)

    except WebSocketDisconnect:
        await manager.disconnect(
            websocket=websocket,
            room_id=room_id,
            user_email=user_db.email,
        )
