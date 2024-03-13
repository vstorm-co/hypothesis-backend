from pydantic import BaseModel, Field


class AnnotationFormBase(BaseModel):
    username: str
    api_key: str
    group: str
    tags: list[str]
    url: str
    response_template: str
    prompt: str
    room_id: str


class AnnotationFormInput(AnnotationFormBase):
    pass


class AnnotationFormOutput(BaseModel):
    status: dict


class TextQuoteSelector(BaseModel):
    exact: str = Field(description="Exact text, maximum words that keep the context")
    prefix: str = Field(description="No longer than 32 chars")
    suffix: str = Field(description="No longer than 32 chars")


class ListOfTextQuoteSelector(BaseModel):
    selectors: list[TextQuoteSelector]


class HypothesisAnnotationCreate(BaseModel):
    pass
