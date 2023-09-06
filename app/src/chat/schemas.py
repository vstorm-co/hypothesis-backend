from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RoomBase(BaseModel):
    name: str | None = None
    share: bool = False


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


class ChatMessage(BaseModel):
    message: str


class MessageDB(BaseModel):
    uuid: UUID
    created_at: datetime
    room_id: UUID
    created_by: str
    content: str


class MessageDetails(BaseModel):
    created_by: str
    room_id: str
    content: str


class RoomDetails(RoomBase):
    uuid: str
    messages: list[MessageDB]
