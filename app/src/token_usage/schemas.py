from datetime import datetime

from pydantic import BaseModel


class TokenUsageBase(BaseModel):
    type: str
    count: int
    value: float


class TokenUsageInput(TokenUsageBase):
    ...


class TokenUsageDB(TokenUsageBase):
    id: int
    created_at: datetime


class TokenUsageDBWithSummedValues(TokenUsageDB):
    # token counts
    prompt_tokens_count: int | None = None
    completion_tokens_count: int | None = None
    total_tokens_count: int | None = None
    # values
    prompt_value: float | None = None
    completion_value: float | None = None
    total_value: float | None = None
