from pydantic import BaseModel


class ChatMessage(BaseModel):
    message: str


class RoomCreate(BaseModel):
    name: str


class RoomCreateWithUserId(RoomCreate):
    user_id: int


class RoomUpdate(BaseModel):
    name: str


class RoomUpdateWithId(RoomUpdate):
    room_id: str


class Room(BaseModel):
    uuid: str
    user_id: int


class Message(BaseModel):
    created_by: str
    room_id: str
    content: str
