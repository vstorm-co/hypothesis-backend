from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.chat.enums import VisibilityChoices
from src.token_usage.schemas import TokenUsageDBWithSummedValues


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
    token_usage_id: int | None = None


class MessageDBWithTokenUsage(MessageDB):
    usage: TokenUsageDBWithSummedValues


class MessagesDeleteInput(BaseModel):
    room_id: str
    date_from: datetime | None = None
    organization_uuid: UUID | None = None


class MessagesDeleteOutput(BaseModel):
    status: str


class RoomDetails(RoomDB):
    messages: list[MessageDBWithTokenUsage]
    owner: int
    prompt_tokens_count: int | None = None
    completion_tokens_count: int | None = None
    total_tokens_count: int | None = None
    prompt_value: float | None = None
    completion_value: float | None = None
    total_value: float | None = None


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


class GlobalConnectMessage(ConnectMessage):
    room_id: str

    def is_equal_except_type(self, other):
        if not isinstance(other, GlobalConnectMessage):
            return False

        return (
            self.room_id == other.room_id
            and self.user_email == other.user_email
            and self.sender_picture == other.sender_picture
            and self.user_name == other.user_name
        )


class CloneChatOutput(BaseModel):
    messages: list[MessageDB]
    chat: RoomDB
