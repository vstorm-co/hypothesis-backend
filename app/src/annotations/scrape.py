from logging import getLogger

from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.annotations.schemas import (
    AnnotationFormInput,
    ListOfTextQuoteSelector,
    TextQuoteSelector,
)
from src.annotations.service import get_selector_from_scrapped_data
from src.scraping.content_loaders import get_content_from_url

logger = getLogger(__name__)


async def _get_url_splits(url: str) -> list[str]:
    """
    Get page content by URL
    """
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=10000, chunk_overlap=0
    )
    content: str = await get_content_from_url(url)
    splits: list[str] = splitter.split_text(content)

    return splits


async def get_hypothesis_selectors(
    data: AnnotationFormInput,
) -> list[TextQuoteSelector]:
    """
    Get selectors from URL
    """
    splits: list[str] = await _get_url_splits(data.url)
    result: dict[str, TextQuoteSelector] = {}

    logger.info(f"Creating selectors from URL: {data.url} with query: {data.prompt}...")
    for split in splits:
        scraped_data: ListOfTextQuoteSelector = get_selector_from_scrapped_data(
            data, split
        )

        for selector in scraped_data.selectors:
            if selector.exact in result:
                continue
            result[selector.exact] = selector

    logger.info(f"Selectors created from URL: {data.url} with query: {data.prompt}!!")
    return list(result.values())
