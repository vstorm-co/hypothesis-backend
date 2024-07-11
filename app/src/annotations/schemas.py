from pydantic import BaseModel, Field

from src.chat.content_cleaner import clean_html_input


class AnnotationFormBase(BaseModel):
    username: str
    api_key: str
    group: str
    tags: list[str]
    url: str
    response_template: str
    prompt: str
    room_id: str
    provider: str = "openai"
    model: str = "gpt-4"
    input_type: str = "url"
    delete_annotations: bool = False


class AnnotationFormInput(AnnotationFormBase):
    def __post_init__(self):
        self.response_template = clean_html_input(self.response_template)
        self.prompt = clean_html_input(self.prompt)


class AnnotationDeleteInput(BaseModel):
    message_uuid: str
    room_id: str
    api_key: str
    url: str
    annotation_ids: list[str]


class AnnotationFormOutput(BaseModel):
    status: dict


class TextQuoteSelector(BaseModel):
    exact: str = Field(
        description="REQUIRED! Exact text, maximum words that keep the context",
        default="",
    )
    prefix: str = Field(description="REQUIRED! No longer than 32 chars", default="")
    suffix: str = Field(description="REQUIRED! No longer than 32 chars", default="")
    annotation: str = Field(
        description="REQUIRED! The text of the quoted annotation", min_length=1
    )


class ListOfTextQuoteSelector(BaseModel):
    selectors: list[TextQuoteSelector]


class HypothesisApiInput(BaseModel):
    room_id: str
    api_key: str


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
