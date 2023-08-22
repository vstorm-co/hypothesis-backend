from pydantic import BaseModel


class ChatMessage(BaseModel):
    message: str


class RoomCreate(BaseModel):
    user_id: str


class Room(BaseModel):
    uuid: str
    user_id: int


class Message(BaseModel):
    created_by: str
    room_id: str
    content: str
