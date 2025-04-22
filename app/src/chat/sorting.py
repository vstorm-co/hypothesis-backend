from fastapi_pagination import Page

from src.chat.schemas import RoomDBWithTokenUsage


def sort_paginated_items(rooms: Page[RoomDBWithTokenUsage]):
    # sort by visibility and active_users_count
    rooms = sorted(
        rooms,
        key=lambda room: (len(room.active_users),),
        reverse=True,
    )

    return rooms
