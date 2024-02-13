from pydantic import BaseModel


class WSEventMessage(BaseModel):
    type: str
    id: str | None = None
