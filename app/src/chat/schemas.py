from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.chat.enums import VisibilityChoices


# Room schemas
class RoomBase(BaseModel):
    name: str | None = None
    share: bool = False
    visibility: str = VisibilityChoices.JUST_ME


class RoomCreateInput(RoomBase):
    pass


class RoomCreateInputDetails(RoomBase):
    user_id: int


class RoomUpdate(RoomBase):
    pass


class RoomUpdateInputDetails(RoomUpdate):
    room_id: str
    user_id: int


class RoomDeleteOutput(BaseModel):
    status: str


class RoomDB(RoomBase):
    uuid: UUID
    created_at: datetime
    user_id: int
    share: bool
    visibility: str


# Message schemas
class ChatMessage(BaseModel):
    message: str


class MessageDetails(BaseModel):
    created_by: str
    room_id: str
    content: str
    user_id: int


class MessageDB(BaseModel):
    uuid: UUID
    created_at: datetime
    room_id: UUID
    created_by: str
    content: str
    user_id: int


class RoomDetails(RoomBase):
    uuid: str
    messages: list[MessageDB]
    visibility: str
