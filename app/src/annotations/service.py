import logging

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src.annotations.constants import text_selector_prompt_template
from src.annotations.custom_pydantic_parser import CustomPydanticOutputParser
from src.annotations.hypothesis_api import get_hypothesis_annotation_by_id
from src.annotations.messaging import create_message_for_users
from src.annotations.schemas import (
    HypothesisAnnotationCreateOutput,
    ListOfTextQuoteSelector,
    TextQuoteSelector,
)
from src.chat.config import settings as chat_settings
from src.chat.constants import MODEL_NAME
from src.chat.schemas import MessageDBWithTokenUsage

logger = logging.getLogger(__name__)


def get_selector_from_scrapped_data(
    query: str, scraped_data: str
) -> ListOfTextQuoteSelector:
    scraped_data = " ".join(scraped_data.strip().split("\n"))
    llm = ChatOpenAI(  # type: ignore
        temperature=0.0,
        model=MODEL_NAME,
        openai_api_key=chat_settings.CHATGPT_KEY,
    )
    parser = CustomPydanticOutputParser(pydantic_object=ListOfTextQuoteSelector)
    prompt = PromptTemplate(
        template=text_selector_prompt_template,
        input_variables=["scraped_data", "query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm | parser

    logger.info(f"Creating selector from scraped data with query: {query}")
    response: ListOfTextQuoteSelector = chain.invoke(
        {
            "query": query,
            "scraped_data": scraped_data,
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
                    get_hypothesis_annotation_by_id(annotation_id)
                )
                if annotation:
                    hypo_annotations_list.append(annotation)
            if not hypo_annotations_list:
                if message.content == "Creating...":
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
