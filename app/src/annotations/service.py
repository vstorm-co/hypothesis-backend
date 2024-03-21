import logging

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src.annotations.constants import text_selector_prompt_template
from src.annotations.custom_pydantic_parser import CustomPydanticOutputParser
from src.annotations.hypothesis_api import get_hypothesis_annotation_by_id
from src.annotations.messaging import create_message_for_users
from src.annotations.schemas import (
    AnnotationFormInput,
    HypothesisAnnotationCreateOutput,
    ListOfTextQuoteSelector,
    TextQuoteSelector,
)
from src.chat.config import settings as chat_settings
from src.chat.constants import MODEL_NAME
from src.chat.schemas import MessageDBWithTokenUsage

logger = logging.getLogger(__name__)


def get_selector_from_scrapped_data(
    data: AnnotationFormInput, scraped_data: str
) -> ListOfTextQuoteSelector:
    # get llm
    llm = ChatOpenAI(  # type: ignore
        temperature=0.0,
        model=MODEL_NAME,
        openai_api_key=chat_settings.CHATGPT_KEY,
    )
    # get parser
    parser = CustomPydanticOutputParser(pydantic_object=ListOfTextQuoteSelector)
    # get prompt
    template = ""
    # check if user defined response template
    if data.response_template:
        template += data.response_template
    template += text_selector_prompt_template
    prompt = PromptTemplate(
        template=template,
        input_variables=["scraped_data", "query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    # get chain
    chain = prompt | llm | parser

    logger.info(f"Creating selector from scraped data with query: {data.prompt}")
    response: ListOfTextQuoteSelector = chain.invoke(
        {
            "query": data.prompt,
            "scraped_data": " ".join(scraped_data.strip().split("\n")),
        }
    )

    # making sure that AI gave only last
    # 32 characters in suffix and prefix
    max_chars = 32
    selector: TextQuoteSelector
    for selector in response.selectors:
        selector.prefix = selector.prefix[-max_chars:]
        selector.suffix = selector.suffix[:max_chars]

    return response


async def check_for_annotation_message_type(
    messages_schema: list[MessageDBWithTokenUsage],
) -> list[MessageDBWithTokenUsage]:
    for index, message in enumerate(messages_schema):
        if message.created_by == "annotation":
            hypo_annotations_list: list[HypothesisAnnotationCreateOutput] = []
            for annotation_id in message.content.split(","):
                annotation: HypothesisAnnotationCreateOutput | None = (
                    get_hypothesis_annotation_by_id(
                        annotation_id,
                        message.content_dict["api_key"]
                        if message.content_dict
                        else None,
                    )
                )
                if annotation:
                    hypo_annotations_list.append(annotation)
            if not hypo_annotations_list:
                if message.content == "Creating...":
                    messages_schema[index].content = ""
                    messages_schema[index].content_html = None
                    continue
                messages_schema[index].content = "No annotations created"
                messages_schema[index].content_html = None
                continue

            messages_schema[index].content = create_message_for_users(
                hypo_annotations_list
            )
            if hypo_annotations_list[0].links:
                messages_schema[index].content_html = hypo_annotations_list[0].links[
                    "incontext"
                ]

    return messages_schema
