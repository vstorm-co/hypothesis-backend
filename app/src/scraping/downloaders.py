from logging import getLogger

from requests import get

from src.google_drive.downloader import get_pdf_file_details
from src.scraping.content_loaders import get_content_from_url, read_docx_from_bytes

logger = getLogger(__name__)


async def download_and_extract_content_from_url(url: str):
    if url.endswith(".txt"):
        logger.info(f"Downloading and extracting txt file from: {url}")
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return

        text = response.text
    elif url.endswith(".doc") or url.endswith(".docx"):
        logger.info(f"Downloading and extracting docx file from: {url}")
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return

        text = read_docx_from_bytes(response.content)
    elif url.endswith(".pdf"):
        logger.info(f"Downloading and extracting pdf file from: {url}")
        details = await get_pdf_file_details(url=url)
        if not details:
            logger.error(f"Failed to download file: {url}")
            return "Empty PDF file."
        text = details["content"]
    elif "youtube" in url:
        # get the data from the url
        from langchain_community.document_loaders import YoutubeLoader

        loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
        docs = loader.load()

        res = ""
        for doc in docs:
            res += doc.page_content

        text = res
    else:
        logger.info(f"Downloading and extracting {url.split('.')[-1]} file from: {url}")
        text = await get_content_from_url(url)

    return text
