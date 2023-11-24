from pydantic import BaseModel


class WSEventMessage(BaseModel):
    type: str
