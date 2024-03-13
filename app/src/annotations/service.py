import logging

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src.annotations.constants import text_selector_prompt_template
from src.annotations.schemas import TextQuoteSelector, ListOfTextQuoteSelector
from src.chat.constants import MODEL_NAME
from src.chat.config import settings as chat_settings

logger = logging.getLogger(__name__)


def get_selector_from_scrapped_data(scraped_data: str) -> ListOfTextQuoteSelector:
    scraped_data = ' '.join(scraped_data.strip().split('\n'))
    llm = ChatOpenAI(
        temperature=0.0,
        model=MODEL_NAME,
        openai_api_key=chat_settings.CHATGPT_KEY,
    )
    parser = PydanticOutputParser(pydantic_object=ListOfTextQuoteSelector)
    prompt = PromptTemplate(
        template=text_selector_prompt_template,
        input_variables=["scraped_data", "query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm | parser
    query = "Get car models from the scraped data"

    logger.info(f"Creating selector from scraped data with query: {query}")
    response: ListOfTextQuoteSelector = chain.invoke(
        {
            "query": query,
            "scraped_data": scraped_data,
        }
    )
    logger.info(f"Selector created: {response.model_dump()}")

    # making sure that AI gave only last
    # 32 characters in suffix and prefix
    max_chars = 32
    selector: TextQuoteSelector
    for selector in response.selectors:
        selector.prefix = selector.prefix[-max_chars:]
        selector.suffix = selector.suffix[:max_chars]

    return response
