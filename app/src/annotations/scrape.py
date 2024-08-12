import json
from datetime import datetime
from logging import getLogger
from time import time

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from src.annotations.constants import (
    DOCUMENT_TITLE_PROMPT_TEMPLATE,
    NUM_OF_SELECTORS_PROMPT_TEMPLATE,
    TEXT_SELECTOR_PROMPT_TEMPLATE,
    YOUTUBE_TRANSCRIPTION_PROMPT_TEMPLATE,
)
from src.annotations.custom_pydantic_parser import CustomPydanticOutputParser
from src.annotations.schemas import (
    AnnotationFormInput,
    ListOfTextQuoteSelector,
    TextQuoteSelector,
)
from src.auth.schemas import UserDB
from src.chat.config import settings as chat_settings
from src.chat.constants import MODEL_NAME
from src.chat.schemas import APIInfoBroadcastData
from src.google_drive.downloader import get_google_drive_file_details
from src.redis import pub_sub_manager
from src.scraping.downloaders import download_and_extract_content_from_url
from src.user_files.constants import UserFileSourceType
from src.user_models.constants import MAX_INPUT_SIZE_MAP
from src.user_models.schemas import UserModelOut
from src.user_models.service import decrypt_api_key, get_model_by_uuid
from src.youtube.service import YouTubeService

logger = getLogger(__name__)


class AnnotationsScraper:
    MAX_CHARS = 32
    DEFAULT_DOCUMENT_TITLE = "Document title"

    def __init__(
        self, input_form_data: AnnotationFormInput, user_db: UserDB | None = None
    ):
        self.data: AnnotationFormInput = input_form_data
        self.splits: list[str] = []
        self.user_db: UserDB | None = user_db
        self.pdf_urn: str | None = None
        self.whole_input = ""
        self.source = "url"
        self.user_model = UserModelOut(
            uuid="",
            provider="",
            defaultSelected="",
            api_key="",
            default=False,
            user=0,
        )

    async def set_models(self):
        user_model_db = await get_model_by_uuid(self.data.user_model_uuid)
        if not user_model_db:
            return

        user_model = UserModelOut(**dict(user_model_db))
        self.user_model = user_model

        if user_model.provider.lower() == "openai":
            self.zero_temp_llm = ChatOpenAI(  # type: ignore
                temperature=0.0,
                model=self.data.model,
                openai_api_key=decrypt_api_key(user_model.api_key),
            )
            self.higher_temp_llm = ChatOpenAI(  # type: ignore
                temperature=0.5,
                model=self.data.model,
                openai_api_key=decrypt_api_key(user_model.api_key),
            )
        elif user_model.provider.lower() == "claude":
            self.zero_temp_llm = ChatAnthropic(  # type: ignore
                temperature=0.0,
                model=self.data.model,
                api_key=decrypt_api_key(user_model.api_key),
            )
            self.higher_temp_llm = ChatAnthropic(  # type: ignore
                temperature=0.5,
                model=self.data.model,
                api_key=decrypt_api_key(user_model.api_key),
            )
        elif user_model.provider.lower() == "groq":
            self.zero_temp_llm = ChatGroq(  # type: ignore
                temperature=0.0,
                model_name=self.data.model,
                groq_api_key=decrypt_api_key(user_model.api_key),
            )
            self.higher_temp_llm = ChatGroq(  # type: ignore
                temperature=0.5,
                model_name=self.data.model,
                groq_api_key=decrypt_api_key(user_model.api_key),
            )

    async def _get_url_splits(self, url: str) -> list[str]:
        """
        Get page content by URL
        """
        content: str
        await pub_sub_manager.publish(
            self.data.room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=self.data.room_id,
                    date=datetime.now().isoformat(),
                    api="Content Loader",
                    type="sent",
                    data={
                        "url": url,
                    },
                ).model_dump(
                    mode="json",
                    exclude={
                        "model",
                    },
                )
            ),
        )
        start_time = time()
        logger.info(f"Annotations: Getting content from URL: {url}")
        if self.data.input_type == UserFileSourceType.URL:
            self.source = UserFileSourceType.URL
            url_data = await download_and_extract_content_from_url(
                url=url, room_id=self.data.room_id, get_urn=True
            )
            if not url_data:
                return []
            content = url_data.get("content", "")
            self.pdf_urn = url_data.get("urn", None)
        elif self.data.input_type == UserFileSourceType.GOOGLE_DRIVE:
            self.source = UserFileSourceType.GOOGLE_DRIVE
            if not self.user_db:
                logger.error("User is missing")
                return []

            logger.info(
                f"Getting PDF file details from Google Drive with file ID: {url}"
            )
            logger.info("User: %s", self.user_db.model_dump())
            data: dict | None = await get_google_drive_file_details(
                file_id=url, user_db=self.user_db
            )
            if not data:
                return []

            logger.info(f"Got PDF file details from Google Drive with file ID: {url}")
            content = data["content"]
            self.pdf_urn = data["urn"]
        else:
            logger.info(f"Unsupported input type: {self.data.input_type}")
            return []

        logger.info(f"Content from URL: {url} has been received")
        await pub_sub_manager.publish(
            self.data.room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=self.data.room_id,
                    date=datetime.now().isoformat(),
                    api="Content Loader",
                    type="recd",
                    elapsed_time=time() - start_time,
                    data={
                        "content": content,
                    },
                ).model_dump(
                    mode="json",
                    exclude={
                        "model",
                    },
                )
            ),
        )

        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=MAX_INPUT_SIZE_MAP.get(self.data.model, 4096),
            chunk_overlap=0,
        )
        splits: list[str] = splitter.split_text(content)

        # Save splits for later use
        self.splits = splits

        return splits

    def set_url_source(self):
        """
        Set URL source
        """
        if any(
            substring in self.data.url
            for substring in ["youtube", "youtu.be", "you.tube"]
        ):
            youtube_service: YouTubeService = YouTubeService()
            self.source = UserFileSourceType.YOUTUBE
            yt_link: str | None = youtube_service.get_youtube_link(self.data.url)
            if yt_link:
                self.data.url = yt_link

    async def get_hypothesis_selectors_data(
        self,
    ) -> dict[str, str | list[TextQuoteSelector]]:
        """
        Get selectors from URL
        """
        await self.set_models()
        splits: list[str] = await self._get_url_splits(self.data.url)

        if not splits:
            return {
                "error": "Content from URL is empty.",
            }

        result: dict[str, TextQuoteSelector] = {}

        # set url source
        self.set_url_source()

        num_of_interesting_selectors = await self._get_num_of_interesting_selectors()

        logger.info(
            f"""Creating selectors from URL: {self.data.url}
        with query: {self.data.prompt}..."""
        )
        for index, split in enumerate(splits):
            logger.info(f"Processing split {index + 1} out of {len(splits)}")

            scraped_data: ListOfTextQuoteSelector = (
                await self._get_selector_from_scrapped_data(split)
            )

            for selector in scraped_data.selectors:
                if selector.exact in result:
                    continue
                result[selector.exact] = selector

            if (
                num_of_interesting_selectors
                and len(list(result.values())) >= num_of_interesting_selectors
            ):
                logger.info(
                    f"Got {num_of_interesting_selectors} selectors, scraping stopped."
                )
                break

        logger.info(
            f"""Selectors created from URL: {self.data.url}
        with query: {self.data.prompt}"""
        )

        selectors = list(result.values())
        if num_of_interesting_selectors:
            """
            So far it works only with
            getting very first `num_of_interesting_selectors` selectors.
            Improve here is to check if user asked for first/last/most
            interesting selectors.
            """
            selectors = selectors[:num_of_interesting_selectors]

        return {
            "selectors": selectors,
        }

    async def _get_num_of_interesting_selectors(self) -> int | None:
        """
        If there are more than 1 split we need to handle the case
        when user asked for specific number of selectors
        because in situation when user asked for 2 selectors,
        and we have 3 splits we are returning 2 selectors for each split.
        To handle this we need to return only the number of selectors
        that user asked for.
        So we need to get the number of interesting selectors from user input.
        If user didn't ask for a specific number of selectors we return None.
        """
        # get llm
        llm = self.zero_temp_llm
        parser = StrOutputParser()
        prompt = PromptTemplate(
            template=NUM_OF_SELECTORS_PROMPT_TEMPLATE,
            input_variables=["question"],
        )

        chain = prompt | llm | parser

        logger.info(
            f"Getting number of interesting selectors with query: {self.data.prompt}"
        )
        model_response = chain.invoke({"question": self.data.prompt})

        logger.info(
            f"Number of interesting selectors (raw model response): '{model_response}'"
        )
        try:
            num_of_selectors = int(model_response)
        except ValueError:
            return None

        return num_of_selectors

    async def _get_selector_from_scrapped_data(
        self, split: str
    ) -> ListOfTextQuoteSelector:
        # get llm
        llm = self.zero_temp_llm
        # get parser
        parser = CustomPydanticOutputParser(pydantic_object=ListOfTextQuoteSelector)
        # get prompt
        template = ""
        # check if user defined response template
        if self.data.response_template:
            template += self.data.response_template

        # use correct prompt template
        if self.source == UserFileSourceType.YOUTUBE:
            template += YOUTUBE_TRANSCRIPTION_PROMPT_TEMPLATE
        else:
            template += TEXT_SELECTOR_PROMPT_TEMPLATE
        prompt = PromptTemplate(
            template=template,
            input_variables=["scraped_data", "prompt", "split_index", "total"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        # get chain
        chain = prompt | llm | parser

        logger.info(
            f"Creating selector from scraped data with query: {self.data.prompt}"
        )

        # prepare scraped data
        scraped_data = " ".join(split.split("\n"))
        scraped_data = scraped_data.replace("\\", "")
        scraped_data = scraped_data.replace("}", "")
        scraped_data = scraped_data.replace("{", "")

        # create input data
        input_data = {
            "scraped_data": scraped_data,
            "prompt": self.data.prompt,
            "split_index": self.splits.index(split) + 1,
            "total": len(self.splits),
        }

        await pub_sub_manager.publish(
            self.data.room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=self.data.room_id,
                    date=datetime.now().isoformat(),
                    api=f"{self.user_model.provider} API",
                    type="sent",
                    data={
                        "template": template,
                        "input": input_data,
                    },
                    model=self.data.model,
                ).model_dump(mode="json")
            ),
        )
        start = time()

        # get the full prompt as a string and save it
        self.whole_input += prompt.format(**input_data)

        response: ListOfTextQuoteSelector = chain.invoke(input_data)
        logger.info(
            f"Selector created from scraped data with query: {self.data.prompt}"
        )

        elapsed_time = time() - start
        logger.info(f"Time taken: {elapsed_time}")

        await pub_sub_manager.publish(
            self.data.room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=self.data.room_id,
                    date=datetime.now().isoformat(),
                    api=f"{self.user_model.provider} API",
                    type="recd",
                    elapsed_time=elapsed_time,
                    data={
                        **response.model_dump(mode="json"),
                    },
                    model=self.data.model,
                ).model_dump(mode="json")
            ),
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

        # llm = self.higher_temp_llm
        # if self.data.provider == "OpenAI":
        #     llm = ChatOpenAI(  # type: ignore
        #         temperature=0.0,
        #         model=self.data.model,
        #         openai_api_key=chat_settings.CHATGPT_KEY,
        #     )
        # elif self.data.provider == "Claude":
        #     llm = ChatAnthropic(  # type: ignore
        #         temperature=0.0,
        #         model=self.data.model,
        #         api_key=chat_settings.CLAUDE_KEY,
        #     )
        llm = ChatOpenAI(  # type: ignore
            temperature=0.0,
            model=MODEL_NAME,
            openai_api_key=chat_settings.CHATGPT_KEY,
        )
        parser = StrOutputParser()
        prompt = PromptTemplate(
            template=DOCUMENT_TITLE_PROMPT_TEMPLATE,
            input_variables=["input"],
        )
        chain = prompt | llm | parser

        logger.info("Getting document title basing on first split")
        return chain.invoke({"input": self.splits[0]})
