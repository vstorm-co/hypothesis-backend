from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ActivateRoomUserBase(BaseModel):
    room_uuid: str
    user_id: int


class ActiveRoomUsersInput(ActivateRoomUserBase):
    pass


class ActiveRoomUsersDB(ActivateRoomUserBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime | None = None
