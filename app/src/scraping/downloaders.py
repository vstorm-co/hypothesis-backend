from logging import getLogger
from urllib.parse import urlparse, urlunparse

from langchain_community.document_loaders import YoutubeLoader
from requests import get

from src.google_drive.downloader import get_pdf_file_details
from src.scraping.content_loaders import get_content_from_url, read_docx_from_bytes

logger = getLogger(__name__)


async def download_and_extract_content_from_url(url: str) -> str | None:
    if url.endswith(".txt"):
        logger.info(f"Downloading and extracting txt file from: {url}")
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return None

        text = response.text
    elif url.endswith(".doc") or url.endswith(".docx"):
        logger.info(f"Downloading and extracting docx file from: {url}")
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return None

        text = read_docx_from_bytes(response.content)
    elif url.endswith(".pdf"):
        logger.info(f"Downloading and extracting pdf file from: {url}")
        details = await get_pdf_file_details(url=url)
        if not details:
            logger.error(f"Failed to download file: {url}")
            return "Empty PDF file."

        text = details["content"]
    elif any(substring in url for substring in ["youtube", "youtu.be", "you.tube"]):
        # get the data from the url
        parsed_url = urlparse(url)

        # remove the query and fragment from the url
        unparsed_url = urlunparse(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", "")
        )

        loader = YoutubeLoader.from_youtube_url(unparsed_url, add_video_info=False)
        docs = loader.load()

        doc_parts = ""
        for doc in docs:
            doc_parts += doc.page_content

        text = doc_parts
    else:
        logger.info(f"Downloading and extracting {url.split('.')[-1]} file from: {url}")
        text = await get_content_from_url(url)

    return text
