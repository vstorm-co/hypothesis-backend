from typing import Optional
from uuid import UUID

from cryptography.fernet import Fernet
from pydantic import BaseModel

from src.config import settings

cipher_suite = Fernet(settings.FERNET_KEY.encode())


class UserModelCreateInput(BaseModel):
    provider: str
    model: str
    api_key: str
    user: int | None = None


class UserModelUpdateInput(BaseModel):
    provider: Optional[str]
    model: Optional[str]
    api_key: Optional[str]
    active: Optional[bool]


class UserModelOut(BaseModel):
    uuid: UUID | str
    provider: str
    model: str
    api_key: str
    active: bool
    user: int


class UserModelDeleteOut(BaseModel):
    status: str
