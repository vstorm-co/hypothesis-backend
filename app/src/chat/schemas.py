from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.chat.enums import VisibilityChoices


# Room schemas
class RoomBase(BaseModel):
    name: str | None = None
    share: bool = False
    visibility: str = VisibilityChoices.JUST_ME
    organization_uuid: UUID | None = None


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


class RoomCloneInput(BaseModel):
    message_id: str | None


class RoomDB(RoomBase):
    uuid: UUID
    user_id: int
    share: bool
    visibility: str
    created_at: datetime
    updated_at: datetime | None


# Message schemas
class ChatMessage(BaseModel):
    message: str


class MessageDetails(BaseModel):
    created_by: str
    room_id: str
    content: str
    user_id: int
    sender_picture: str | None = None
    content_html: str | None = None


class MessageDB(BaseModel):
    uuid: UUID
    created_at: datetime
    room_id: UUID
    created_by: str
    content: str
    user_id: int
    updated_at: datetime | None = None
    sender_picture: str | None = None
    content_html: str | None = None


class RoomDetails(RoomDB):
    messages: list[MessageDB]
    owner: int


class BroadcastData(BaseModel):
    type: str | None = None
    message: str
    room_id: str
    sender_user_email: str
    created_by: str = "user"
    sender_picture: str | None = None
    sender_name: str | None = None
    message_html: str | None = None


class ConnectMessage(BaseModel):
    type: str
    user_email: str
    sender_picture: str | None = None
    user_name: str | None = None
