from logging import getLogger

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src.annotations.constants import (
    DOCUMENT_TITLE_PROMPT_TEMPLATE,
    TEXT_SELECTOR_PROMPT_TEMPLATE,
    UNIQUE_TEXT_SELECTOR_PROMPT_TEMPLATE,
)
from src.annotations.custom_pydantic_parser import CustomPydanticOutputParser
from src.annotations.schemas import (
    AnnotationFormInput,
    ListOfTextQuoteSelector,
    TextQuoteSelector,
)
from src.chat.config import settings as chat_settings
from src.chat.constants import MODEL_NAME
from src.scraping.content_loaders import get_content_from_url

logger = getLogger(__name__)


class AnnotationsScraper:
    MAX_CHARS = 32
    DEFAULT_DOCUMENT_TITLE = "Document title"

    def __init__(self, data: AnnotationFormInput):
        self.data: AnnotationFormInput = data
        self.splits: list[str] = []

    async def _get_url_splits(self, url: str) -> list[str]:
        """
        Get page content by URL
        """
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=10000, chunk_overlap=0
        )
        content: str = await get_content_from_url(url)
        splits: list[str] = splitter.split_text(content)

        # Save splits for later use
        self.splits = splits

        return splits

    async def get_hypothesis_selectors(self) -> list[TextQuoteSelector]:
        """
        Get selectors from URL
        """
        splits: list[str] = await self._get_url_splits(self.data.url)
        result: dict[str, TextQuoteSelector] = {}

        logger.info(
            f"""
        Creating selectors from URL: {self.data.url} with query: {self.data.prompt}...
        """
        )
        for index, split in enumerate(splits):
            logger.info(f"Processing split {index + 1} out of {len(splits)}")

            scraped_data: ListOfTextQuoteSelector = (
                self.get_selector_from_scrapped_data(split)
            )

            for selector in scraped_data.selectors:
                if selector.exact in result:
                    continue
                result[selector.exact] = selector

        logger.info(
            f"""Selectors created from URL: {self.data.url}
        with query: {self.data.prompt}"""
        )
        return list(result.values())

    def get_selector_from_scrapped_data(self, split: str) -> ListOfTextQuoteSelector:
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
        if self.data.response_template:
            template += self.data.response_template
        template += TEXT_SELECTOR_PROMPT_TEMPLATE
        prompt = PromptTemplate(
            template=template,
            input_variables=["scraped_data", "query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        # get chain
        chain = prompt | llm | parser

        logger.info(
            f"Creating selector from scraped data with query: {self.data.prompt}"
        )
        response: ListOfTextQuoteSelector = chain.invoke(
            {
                "query": self.data.prompt,
                "scraped_data": " ".join(split.strip().split("\n")),
            }
        )

        # making sure that AI gave only last
        # MACH_CHARS characters in suffix and prefix
        selector: TextQuoteSelector
        max_chars = self.MAX_CHARS  # need to be done because of E203 mypy
        for selector in response.selectors:
            selector.prefix = selector.prefix[-max_chars:]
            selector.suffix = selector.suffix[:max_chars]

        return response

    def get_document_title_from_first_split(self) -> str:
        """
        Get document title from first split
        """
        if not self.splits:
            return self.DEFAULT_DOCUMENT_TITLE

        llm = ChatOpenAI(  # type: ignore
            temperature=0.5,
            model=MODEL_NAME,
            openai_api_key=chat_settings.CHATGPT_KEY,
        )
        parser = StrOutputParser()
        prompt = PromptTemplate(
            template=DOCUMENT_TITLE_PROMPT_TEMPLATE,
            input_variables=["input"],
        )
        chain = prompt | llm | parser

        logger.info(f"Getting document title from first split: {self.splits[0]}")
        return chain.invoke({"input": self.splits[0]})

    def get_unique_text_for_a_selector_exact(self, selector: str):
        """
        Get unique text for a selector exact
        """
        llm = ChatOpenAI(  # type: ignore
            temperature=0.5,
            model=MODEL_NAME,
            openai_api_key=chat_settings.CHATGPT_KEY,
        )
        parser = StrOutputParser()
        prompt = PromptTemplate(
            template=UNIQUE_TEXT_SELECTOR_PROMPT_TEMPLATE,
            input_variables=["selector", "question"],
        )
        chain = prompt | llm | parser

        logger.info(f"Getting unique text for a selector exact: {self.data.prompt}")
        return chain.invoke(
            {
                "selector": selector,
                "question": self.data.prompt,
            }
        )
