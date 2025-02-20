import json
import logging
from json import JSONDecodeError

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi_filter import FilterDepends

from src.active_room_users.service import (
    clean_user_from_active_rooms,
    create_active_room_user_in_db,
)
from src.auth.exceptions import AuthRequired, UserNotFound
from src.auth.jwt import parse_jwt_user_data, parse_jwt_user_data_optional
from src.auth.schemas import JWTData, UserDB
from src.auth.service import get_user_by_id, get_user_by_token
from src.chat.bot_ai import bot_ai, create_bot_answer_task
from src.chat.constants import MODEL_NAME
from src.chat.exceptions import RoomAlreadyExists, RoomCannotBeCreated, RoomDoesNotExist
from src.chat.filters import RoomFilter, get_query_filtered_by_visibility
from src.chat.pagination import add_room_data
from src.chat.redis_history import get_message_history
from src.chat.schemas import (
    BroadcastData,
    CloneChatOutput,
    MessageDB,
    MessageDBWithTokenUsage,
    MessageDetails,
    MessagesDeleteInput,
    MessagesDeleteOutput,
    RoomCloneInput,
    RoomCreateInput,
    RoomCreateInputDetails,
    RoomDB,
    RoomDBWithTokenUsageAndMessages,
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
    get_non_deleted_messages,
    get_organization_rooms_from_db,
    get_room_by_id_from_db,
    get_room_messages_from_db,
    get_room_messages_to_specific_message,
    update_room_in_db,
)
from src.chat.sorting import sort_paginated_items
from src.chat.validators import is_room_private, not_shared_for_organization
from src.config import settings
from src.constants import Environment
from src.datetime_utils import aware_datetime_field
from src.elapsed_time.service import get_room_elapsed_time_by_messages
from src.listener.constants import (
    bot_message_creation_finished_info,
    listener_room_name,
    room_changed_info,
    stop_generation_finished_info,
)
from src.listener.manager import ws_manager
from src.listener.schemas import WSEventMessage
from src.organizations.security import is_user_in_organization
from src.pagination_utils import enrich_paginated_items
from src.redis_client import pub_sub_manager
from src.tasks import celery_app
from src.token_usage.schemas import TokenUsageDBWithSummedValues
from src.token_usage.service import get_room_token_usages_by_messages
from src.user_models.constants import get_available_models

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/rooms")
async def get_rooms(
    visibility: str | None = None,
    organization_uuid: str | None = None,
    name__ilike: str | None = None,
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
        visibility,
        jwt_data.user_id,
        organization_uuid,
        name__ilike,
    )

    filtered_query = room_filter.filter(query)
    sorted_query = room_filter.sort(filtered_query)

    from src.database import database

    rooms_db = await database.fetch_all(sorted_query)
    rooms = [RoomDBWithTokenUsageAndMessages(**dict(room)) for room in rooms_db]
    enrich_paginated_items(rooms)
    await add_room_data(rooms)
    sort_paginated_items(rooms)

    return {
        "items": rooms,
    }


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
    room_id: str,
    user_join: bool = False,
    jwt_data: JWTData | None = Depends(parse_jwt_user_data_optional),
):
    room = await get_room_by_id_from_db(room_id)
    if not room:
        raise RoomDoesNotExist()

    room_schema = RoomDB(**dict(room))

    if room_schema.share:
        user_schema = None
        if jwt_data:
            user = await get_user_by_id(jwt_data.user_id)
            if user:
                user_schema = UserDB(**dict(user))
    else:
        if not jwt_data:
            raise AuthRequired()

        user = await get_user_by_id(jwt_data.user_id)
        if not user:
            raise UserNotFound()
        user_schema = UserDB(**dict(user))

        if is_room_private(room_schema, user_schema.id):
            raise RoomDoesNotExist()

        if await not_shared_for_organization(room_schema, user_schema.id):
            raise RoomDoesNotExist()

    if user_join and jwt_data:
        await create_active_room_user_in_db(room_id, jwt_data.user_id)

    room_owner_user = await get_user_by_id(room_schema.user_id)
    if not room_owner_user:
        raise UserNotFound()

    messages = await get_room_messages_from_db(room_id)
    messages_schema: list[MessageDBWithTokenUsage] = [
        MessageDBWithTokenUsage(
            **dict(message),
            usage=TokenUsageDBWithSummedValues(
                **{
                    "id": message["token_usage_id"],
                    "type": message["type"],
                    "count": message["count"],
                    "value": message["value"],
                    "created_at": message["created_at_1"],
                }
            ),
        )
        for message in messages
    ]

    token_usage_data: dict = get_room_token_usages_by_messages(messages_schema)
    elapsed_time_data: dict = get_room_elapsed_time_by_messages(messages_schema)

    room_schema.created_at = aware_datetime_field(room_schema.created_at)
    room_schema.updated_at = aware_datetime_field(room_schema.updated_at)

    model_used = None
    provider = None
    if messages_schema and messages_schema[-1].content_dict:
        model_used = messages_schema[-1].content_dict.get("model_used", None)
        if model_used:
            # Get all available models without API key
            available_models, _ = await get_available_models()

            # Check each provider's models
            for provider_name, models in available_models.items():
                if model_used in models:
                    provider = provider_name.lower()
                    break

            # If provider not found in available models, try to infer from model name
            if not provider and isinstance(model_used, str):
                if model_used.startswith(("gpt-", "text-")):
                    provider = "openai"
                elif model_used.startswith("claude"):
                    provider = "claude"
                elif model_used.startswith(("llama", "mixtral")):
                    provider = "groq"

    return RoomDetails(
        **room_schema.model_dump(),
        owner=room_schema.user_id,
        messages=messages_schema,
        prompt_tokens_count=token_usage_data["prompt_tokens_count"],
        completion_tokens_count=token_usage_data["completion_tokens_count"],
        total_tokens_count=token_usage_data["prompt_tokens_count"]
        + token_usage_data["completion_tokens_count"],
        prompt_value=token_usage_data["prompt_value"],
        completion_value=token_usage_data["completion_value"],
        total_value=token_usage_data["prompt_value"]
        + token_usage_data["completion_value"],
        elapsed_time=elapsed_time_data["elapsed_time"],
        model_name=model_used or MODEL_NAME,
        provider=provider or "openai",
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

    if settings.ENVIRONMENT != Environment.TESTING:
        await pub_sub_manager.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(
                    type=room_changed_info,
                    id=room_id,
                    source="room_update",
                ).model_dump(mode="json")
            ),
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
async def clone_room(
    room_id: str, data: RoomCloneInput, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    messages = await get_room_messages_to_specific_message(room_id, data.message_id)
    chat = await get_room_by_id_from_db(room_id)
    if not chat:
        raise RoomDoesNotExist()
    chat_data = RoomCreateInputDetails(**dict(chat))
    chat_data.user_id = jwt_data.user_id
    chat_data.name = f"Copy of {chat_data.name}"
    chat_data.visibility = "just_me"
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
            elapsed_time=message["elapsed_time"],
            content_dict=message["content_dict"],
        )
        await create_message_in_db(message_detail)

    if settings.ENVIRONMENT != Environment.TESTING:
        await pub_sub_manager.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(
                    type=room_changed_info,
                    id=str(created_chat["uuid"]),
                    source="room_clone",
                ).model_dump(mode="json")
            ),
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
    if settings.ENVIRONMENT != Environment.TESTING:
        await pub_sub_manager.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(
                    type=room_changed_info,
                    id=input_data.room_id,
                    source="messages_delete",
                ).model_dump(mode="json")
            ),
        )

    # update redis chat message history
    memory = get_message_history(str(input_data.room_id))
    memory.clear()

    non_deleted_messages = await get_non_deleted_messages(
        room_id=input_data.room_id, date_from=input_data.date_from
    )

    for message in non_deleted_messages:
        if message.created_by == "bot":
            memory.add_ai_message(message.content)
        elif message.created_by == "user":
            memory.add_user_message(message.content)
        else:
            continue

    return MessagesDeleteOutput(status="success")


@router.websocket("/ws/{room_id}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token")
    user_db: UserDB = await get_user_by_token(token)
    bot_ai.user_id = user_db.id
    bot_ai.room_id = room_id

    await websocket.accept()
    logger.info("Adding user to room")
    await ws_manager.add_user_to_room(
        room_id=room_id, websocket=websocket, user=user_db
    )
    logger.info("Informing users about new user in room")
    await ws_manager.update_user_of_users_in_chat(room_id, user_db)
    logger.info("Broadcast info about user joined room")
    await pub_sub_manager.publish(
        room_id,
        json.dumps(
            {
                "type": "user_joined",
                "user_email": user_db.email,
                "sender_picture": user_db.picture,
                "user_name": user_db.name,
            }
        ),
    )
    task_id = None
    try:
        while True:
            # get user message
            data = await websocket.receive_text()
            data_dict = json.loads(data)
            if data_dict["type"] == "user_typing":
                await pub_sub_manager.publish(
                    room_id,
                    json.dumps(
                        {
                            "type": "typing",
                            "content": f"{user_db.name}",
                            "sender_user_email": user_db.email,
                        }
                    ),
                )
            if data_dict["type"] == "message":
                logger.info(f"User message received: {data_dict['content']}")
                bot_ai.stop_generation_flag = False
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
                await pub_sub_manager.publish(
                    room_id, json.dumps(user_broadcast_data.model_dump(mode="json"))
                )
                # create user message in db
                content_to_db = MessageDetails(
                    created_by="user",
                    content=data_dict["content"],
                    content_html=data_dict.get("content_html"),
                    room_id=room_id,
                    user_id=user_db.id,
                    sender_picture=user_db.picture,
                )
                logger.info("Creating message in db")
                await create_message_in_db(content_to_db)
                logger.info("Message created in db")
                await pub_sub_manager.publish(
                    listener_room_name,
                    json.dumps(
                        WSEventMessage(
                            type=room_changed_info,
                            id=room_id,
                            source="new-message",
                        ).model_dump(mode="json")
                    ),
                )

                # update room updated_at
                await update_room_in_db(
                    RoomUpdateInputDetails(
                        room_id=room_id,
                        user_id=user_db.id,
                    ),
                    update_share=False,
                    update_visibility=False,
                )

                # make sure to update correct room id
                bot_ai.room_id = room_id
                logger.info("Creating bot answer task")

                # apply async
                result = create_bot_answer_task.apply_async(
                    args=[data_dict, room_id, user_db.model_dump()],
                    countdown=0,
                )
                logger.info(f"Task ID: {result.task_id}")
                task_id = result.task_id
            if data_dict["type"] == "stop_generation":
                # Set the flag to stop generation
                result = AsyncResult(task_id, app=celery_app)
                result.revoke(terminate=True)

                bot_ai.stop_generation_flag = True

                await pub_sub_manager.publish(
                    room_id,
                    json.dumps(
                        WSEventMessage(
                            type=stop_generation_finished_info,
                            id=room_id,
                            source="stop_generation",
                        ).model_dump(mode="json")
                    ),
                )
                await pub_sub_manager.publish(
                    room_id,
                    json.dumps(
                        WSEventMessage(
                            type=bot_message_creation_finished_info,
                            id=room_id,
                            source="bot-message-creation-finished",
                        ).model_dump(mode="json")
                    ),
                )

                continue  # Skip the rest of the loop for this message

    except WebSocketDisconnect as e:
        await clean_user_from_active_rooms(user_db.id)
        await pub_sub_manager.publish(
            room_id,
            json.dumps(
                {
                    "type": "user_left",
                    "user_email": user_db.email,
                    "sender_picture": user_db.picture,
                    "user_name": user_db.name,
                }
            ),
        )
        logger.info("WebSocket connection closed")
        await pub_sub_manager.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(
                    type=room_changed_info,
                    id=listener_room_name,
                ).model_dump(mode="json")
            ),
        )
        await ws_manager.remove_user_from_room(
            room_id=room_id, websocket=websocket, user=user_db
        )
        logger.info(f"WebSocket disconnected: {e}")
    except JSONDecodeError as e:
        # Handle JSON decoding errors
        logger.error(f"Error decoding JSON: {e}")
    except Exception as e:
        # Handle other exceptions
        logger.error(f"An unexpected error occurred: {e}")
