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


async def add_room_data(page_items: Sequence[RoomDBWithTokenUsage]):
    # Use dictionary comprehension to reduce calls to get active users and messages
    messages_for_all_rooms = {
        str(room.uuid): await get_room_messages_from_db(str(room.uuid))
        for room in page_items
    }
    active_users_for_all_rooms = {
        str(room.uuid): await get_room_active_users_from_db(str(room.uuid))
        for room in page_items
    }

    for room in page_items:
        messages = messages_for_all_rooms[str(room.uuid)]
        active_users = active_users_for_all_rooms[str(room.uuid)]

        # Create message objects only once
        messages_schema = [
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

        # Use a single loop to calculate all token and value counts
        prompt_tokens_count = completion_tokens_count = 0
        prompt_value = completion_value = 0.0
        elapsed_time = 0.0

        for message in messages_schema:
            if message.usage.type == "prompt":
                prompt_tokens_count += message.usage.count
                prompt_value += message.usage.value
            elif message.usage.type == "completion":
                completion_tokens_count += message.usage.count
                completion_value += message.usage.value

            if isinstance(message.elapsed_time, float):
                elapsed_time += message.elapsed_time

        total_tokens_count = prompt_tokens_count + completion_tokens_count
        total_value = prompt_value + completion_value

        # Set attributes
        room.__setattr__("prompt_tokens_count", prompt_tokens_count)
        room.__setattr__("completion_tokens_count", completion_tokens_count)
        room.__setattr__("total_tokens_count", total_tokens_count)
        room.__setattr__("prompt_value", prompt_value)
        room.__setattr__("completion_value", completion_value)
        room.__setattr__("total_value", total_value)
        room.__setattr__("elapsed_time", elapsed_time)
        room.__setattr__("active_users", active_users)
