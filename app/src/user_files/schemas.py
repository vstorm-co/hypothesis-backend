import uuid as uuid
from datetime import datetime

from pydantic import BaseModel


class UserFileDB(BaseModel):
    uuid: uuid.UUID
    source_type: str
    source_value: str
    title: str
    user: int
    created_at: datetime
    updated_at: datetime
    content: str | None = None
    optimized_content: str | None = None
    extension: str | None = None


class CreateUserFileInput(BaseModel):
    source_type: str
    source_value: str
    title: str | None = None
    content: str | None = None
    optimized_content: str | None = None
    extension: str | None = None
    room_id: str | None = None
    id: str | None = None
    mime_type: str | None = None


class DeleteUserFileOutput(BaseModel):
    status: str


class NewUserFileContent(BaseModel):
    content: str
    optimized_content: str | None
