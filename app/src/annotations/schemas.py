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
    exact: str = Field(
        description="Exact text, maximum words that keep the context", default=""
    )
    prefix: str = Field(description="No longer than 32 chars", default="")
    suffix: str = Field(description="No longer than 32 chars", default="")
    annotation: str = Field(description="qute annotation", default="")


class ListOfTextQuoteSelector(BaseModel):
    selectors: list[TextQuoteSelector]


class HypothesisSelector(BaseModel):
    exact: str
    prefix: str
    suffix: str
    type: str = "TextQuoteSelector"


class HypothesisTarget(BaseModel):
    source: str
    selector: list[HypothesisSelector]


class HypothesisAnnotationCreateInput(BaseModel):
    uri: str
    document: dict
    text: str
    tags: list[str] | None
    group: str
    permissions: dict
    target: list[HypothesisTarget]
    # target: list[dict]
    references: list[str]


class HypothesisAnnotationCreateOutput(BaseModel):
    id: str
    created: str
    updated: str
    user: str
    uri: str
    text: str
    tags: list[str]
    group: str
    permissions: dict
    target: list[HypothesisTarget]
    # target: list[dict]
    consumer: str = ""
    references: list[str] = []
    user_info: dict = {}
    links: dict = {}
