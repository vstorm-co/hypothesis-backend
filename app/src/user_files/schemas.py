import uuid as uuid

from pydantic import BaseModel


class UserFileDB(BaseModel):
    uuid: uuid.UUID
    source: str
    title: str
    user: int
    content: str | None = None


class CreateUserFileInput(BaseModel):
    source: str
    title: str
    content: str | None = None


class DeleteUserFileOutput(BaseModel):
    status: str
