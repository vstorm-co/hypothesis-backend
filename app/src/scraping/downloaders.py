from logging import getLogger

from requests import get

from src.scraping.content_loaders import get_content_from_url, read_docx_from_bytes

logger = getLogger(__name__)


async def download_and_extract_content_from_url(url: str):
    if url.endswith(".txt"):
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return

        text = response.text
    elif url.endswith(".doc") or url.endswith(".docx"):
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return

        text = read_docx_from_bytes(response.content)
    else:
        logger.info(f"Downloading and extracting file from: {url}")
        text = await get_content_from_url(url)

    return text
