from typing import Sequence

from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from sqlalchemy.sql.selectable import Select

from src.active_room_users.service import get_room_active_users_from_db
from src.chat.schemas import MessageDBWithTokenUsage, RoomDBWithTokenUsage
from src.chat.service import get_room_messages_from_db
from src.database import database
from src.token_usage.schemas import TokenUsageDBWithSummedValues


async def paginate_rooms(query: Select) -> Page[RoomDBWithTokenUsage]:
    return await paginate(database, query)


async def add_token_usage_fields(page_items: Sequence[RoomDBWithTokenUsage]):
    for room in page_items:
        messages = await get_room_messages_from_db(str(room.uuid))
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
        # calculate tokens
        prompt_tokes_count: int = sum(
            [
                message.usage.count
                for message in messages_schema
                if message.usage.type == "prompt"
            ]
        )
        completion_tokes_count: int = sum(
            [
                message.usage.count
                for message in messages_schema
                if message.usage.type == "completion"
            ]
        )
        total_tokes_count: int = prompt_tokes_count + completion_tokes_count

        # calculate values
        prompt_value: float = sum(
            [
                message.usage.value
                for message in messages_schema
                if message.usage.type == "prompt"
            ]
        )
        completion_value: float = sum(
            [
                message.usage.value
                for message in messages_schema
                if message.usage.type == "completion"
            ]
        )
        total_value: float = prompt_value + completion_value

        # set attrs
        room.__setattr__("prompt_tokens_count", prompt_tokes_count)
        room.__setattr__("completion_tokens_count", completion_tokes_count)
        room.__setattr__("total_tokens_count", total_tokes_count)
        room.__setattr__("prompt_value", prompt_value)
        room.__setattr__("completion_value", completion_value)
        room.__setattr__("total_value", total_value)


async def add_time_elapsed(page_items: Sequence[RoomDBWithTokenUsage]):
    for room in page_items:
        messages = await get_room_messages_from_db(str(room.uuid))
        sum_elapsed_time_value: float = sum(
            [
                message["elapsed_time"]
                for message in messages
                if isinstance(message["elapsed_time"], float)
            ]
        )

        room.__setattr__("elapsed_time", sum_elapsed_time_value)


async def add_active_users(page_items: Sequence[RoomDBWithTokenUsage]):
    for room in page_items:
        active_users = await get_room_active_users_from_db(str(room.uuid))

        room.__setattr__("active_users", active_users)
