import json
import logging
from json import JSONDecodeError

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi_filter import FilterDepends
from fastapi_pagination import Page

from src.auth.exceptions import UserNotFound
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData, UserDB
from src.auth.service import get_user_by_id, get_user_by_token
from src.chat.chatting import HypoAI
from src.chat.exceptions import RoomAlreadyExists, RoomCannotBeCreated, RoomDoesNotExist
from src.chat.filters import RoomFilter, get_query_filtered_by_visibility
from src.chat.manager import ConnectionManager
from src.chat.pagination import paginate_rooms
from src.chat.schemas import (
    BroadcastData,
    CloneChatOutput,
    MessageDB,
    MessageDetails,
    MessagesDeleteInput,
    MessagesDeleteOutput,
    RoomCloneInput,
    RoomCreateInput,
    RoomCreateInputDetails,
    RoomDB,
    RoomDeleteOutput,
    RoomDetails,
    RoomUpdate,
    RoomUpdateInputDetails,
)
from src.chat.service import (
    create_message_in_db,
    create_room_in_db,
    delete_messages_from_db,
    delete_room_from_db,
    get_organization_rooms_from_db,
    get_room_by_id_from_db,
    get_room_messages_from_db,
    get_room_messages_to_specific_message,
    update_room_in_db,
)
from src.chat.validators import is_room_private, not_shared_for_organization
from src.datetime_utils import aware_datetime_fields
from src.listener.constants import bot_message_creation_finished_info, room_changed_info
from src.listener.manager import listener
from src.listener.schemas import WSEventMessage
from src.organizations.security import is_user_in_organization

router = APIRouter()

manager = ConnectionManager()
logger = logging.getLogger(__name__)


@router.get("/rooms", response_model=Page[RoomDB])
async def get_rooms(
    visibility: str | None = None,
    organization_uuid: str | None = None,
    room_filter: RoomFilter = FilterDepends(RoomFilter),
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if organization_uuid and not await is_user_in_organization(
        jwt_data.user_id, str(organization_uuid)
    ):
        # User is not in the organization
        # thus he cannot see the rooms
        raise RoomDoesNotExist()

    query = await get_query_filtered_by_visibility(
        visibility, jwt_data.user_id, organization_uuid
    )

    filtered_query = room_filter.filter(query)
    sorted_query = room_filter.sort(filtered_query)

    rooms = await paginate_rooms(sorted_query)
    aware_datetime_fields(rooms.items)

    return rooms


@router.get("/organization-rooms/{organization_uuid}", response_model=list[RoomDB])
async def get_rooms_by_organization(
    organization_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    if not organization_uuid or not await is_user_in_organization(
        jwt_data.user_id, organization_uuid
    ):
        # User is not in the organization
        # thus he cannot see the rooms
        return []

    rooms = await get_organization_rooms_from_db(organization_uuid)

    return [RoomDB(**dict(room)) for room in rooms]


@router.get("/room/{room_id}", response_model=RoomDetails)
async def get_room_with_messages(
    room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    room = await get_room_by_id_from_db(room_id)
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
    if await not_shared_for_organization(room_schema, user_schema.id):
        raise RoomDoesNotExist()

    # get messages
    messages = await get_room_messages_from_db(room_id)
    messages_schema = [MessageDB(**dict(message)) for message in messages]

    return RoomDetails(
        **room_schema.model_dump(),
        owner=room_schema.user_id,
        messages=messages_schema,
    )


@router.post("/room", response_model=RoomDB)
async def create_room(
    room_data: RoomCreateInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if room_data.organization_uuid and not await is_user_in_organization(
        jwt_data.user_id, str(room_data.organization_uuid)
    ):
        # User is not in the organization
        # thus he cant share the room with the organization
        raise RoomCannotBeCreated()

    room_input_data = RoomCreateInputDetails(
        **room_data.model_dump(), user_id=jwt_data.user_id
    )
    room = await create_room_in_db(room_input_data)

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
    if room_data.organization_uuid and not await is_user_in_organization(
        jwt_data.user_id, str(room_data.organization_uuid)
    ):
        # User is not in the organization
        # thus he cannot see the rooms
        raise RoomDoesNotExist()

    room_update_details = RoomUpdateInputDetails(
        **room_data.model_dump(),
        room_id=room_id,
        user_id=jwt_data.user_id,
    )
    room = await update_room_in_db(room_update_details)

    if not room:
        raise RoomDoesNotExist()

    await listener.receive_and_publish_message(
        WSEventMessage(type=room_changed_info).model_dump(mode="json")
    )

    return RoomDB(**dict(room))


@router.delete("/room/{room_id}", response_model=RoomDeleteOutput)
async def delete_room(
    room_id: str,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    await delete_room_from_db(room_id, jwt_data.user_id)

    return RoomDeleteOutput(status="success")


@router.post("/clone-room/{room_id}", response_model=CloneChatOutput)
async def clone_room(room_id: str, data: RoomCloneInput):
    messages = await get_room_messages_to_specific_message(room_id, data.message_id)
    chat = await get_room_by_id_from_db(room_id)
    if not chat:
        raise RoomDoesNotExist()
    chat_data = RoomCreateInputDetails(**dict(chat))
    chat_data.name = f"Copy of {chat_data.name}"
    created_chat = await create_room_in_db(chat_data)
    if not created_chat:
        raise RoomAlreadyExists()
    for message in messages:
        message_detail = MessageDetails(
            created_by=message["created_by"],
            room_id=str(created_chat["uuid"]),
            content=message["content"],
            user_id=message["user_id"],
            sender_picture=message["sender_picture"],
            content_html=message["content_html"],
        )
        await create_message_in_db(message_detail)
    await listener.receive_and_publish_message(
        WSEventMessage(type=room_changed_info).model_dump(mode="json")
    )
    return CloneChatOutput(
        messages=[MessageDB(**dict(message)) for message in messages],
        chat=RoomDB(**dict(created_chat)),
    )


@router.get("/messages", response_model=list[MessageDB])
async def get_messages(room_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)):
    messages = await get_room_messages_from_db(room_id)

    return [MessageDB(**dict(message)) for message in messages]


@router.delete("/messages", response_model=MessagesDeleteOutput)
async def delete_messages(
    input_data: MessagesDeleteInput, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    if input_data.organization_uuid and not await is_user_in_organization(
        jwt_data.user_id, str(input_data.organization_uuid)
    ):
        # User is not in the organization
        # thus he cannot see the rooms
        raise RoomDoesNotExist()

    await delete_messages_from_db(
        room_id=input_data.room_id, date_from=input_data.date_from
    )
    await listener.receive_and_publish_message(
        WSEventMessage(type=room_changed_info).model_dump(mode="json")
    )

    return MessagesDeleteOutput(status="success")


@router.websocket("/ws/{room_id}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token")
    user_db = await get_user_by_token(token)
    hypo_ai = HypoAI(user_id=user_db.id, room_id=room_id)

    await manager.connect(websocket=websocket, room_id=room_id, user=user_db)
    try:
        while True:
            # get user message
            data = await websocket.receive_text()
            data_dict = json.loads(data)
            if data_dict["type"] == "user_typing":
                await manager.user_typing(user_db, room_id)
            if data_dict["type"] == "message":
                user_broadcast_data = BroadcastData(
                    type="message",
                    message=data_dict["content"],
                    message_html=data_dict.get("content_html"),
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
                    content=data_dict["content"],
                    content_html=data_dict.get("content_html"),
                    room_id=room_id,
                    user_id=user_db.id,
                    sender_picture=user_db.picture,
                )
                await create_message_in_db(content_to_db)
                await listener.receive_and_publish_message(
                    WSEventMessage(type=room_changed_info).model_dump(mode="json")
                )

                # update room updated_at
                await update_room_in_db(
                    RoomUpdateInputDetails(
                        room_id=room_id,
                        user_id=user_db.id,
                    ),
                    update_share=False,
                )

                # chat with chatbot
                bot_answer = ""
                async for message in hypo_ai.chat_with_chat(
                    input_message=data_dict["content"]
                ):
                    bot_answer += message
                    bot_broadcast_data = BroadcastData(
                        type="message",
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
                await create_message_in_db(bot_content)
                await listener.receive_and_publish_message(
                    WSEventMessage(type=bot_message_creation_finished_info).model_dump(
                        mode="json"
                    )
                )
                await listener.receive_and_publish_message(
                    WSEventMessage(type=room_changed_info).model_dump(mode="json")
                )

    except WebSocketDisconnect as e:
        await manager.disconnect(
            room_id=room_id,
            user=user_db,
        )
        logger.error(f"WebSocket disconnected: {e}")
    except JSONDecodeError as e:
        # Handle JSON decoding errors
        logger.error(f"Error decoding JSON: {e}")
    except Exception as e:
        # Handle other exceptions
        logger.error(f"An unexpected error occurred: {e}")
