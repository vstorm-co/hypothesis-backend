import uuid as uuid

from pydantic import BaseModel


class UserFileDB(BaseModel):
    uuid: uuid.UUID
    source_type: str
    source_value: str
    title: str
    user: int
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


class DeleteUserFileOutput(BaseModel):
    status: str


class NewUserFileContent(BaseModel):
    content: str
    optimized_content: str | None
