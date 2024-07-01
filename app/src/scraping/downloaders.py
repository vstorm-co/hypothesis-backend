from logging import getLogger

from langchain_community.document_loaders import YoutubeLoader
from requests import get, head

from src.google_drive.downloader import get_pdf_file_details
from src.scraping.content_loaders import get_content_from_url, read_docx_from_bytes
from src.youtube.service import YouTubeService

logger = getLogger(__name__)

youtube_service: YouTubeService = YouTubeService()


async def download_and_extract_content_from_url(url: str) -> str | None:
    response = head(url, allow_redirects=True, stream=True)
    content_type = response.headers.get("Content-Type", "")

    if "text/plain" in content_type:
        logger.info(f"Downloading and extracting txt file from: {url}")
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return None

        text = response.text
    elif (
        "application/msword" in content_type
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in content_type
    ):
        logger.info(f"Downloading and extracting docx file from: {url}")
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return None

        text = read_docx_from_bytes(response.content)
    elif "application/pdf" in content_type:
        logger.info(f"Downloading and extracting pdf file from: {url}")
        details = await get_pdf_file_details(url=url)
        if not details:
            logger.error(f"Failed to download file: {url}")
            return "Empty PDF file."

        text = details["content"]
    elif any(substring in url for substring in ["youtube", "youtu.be", "you.tube"]):
        link: str | None = youtube_service.get_youtube_link(url)
        if not link:
            logger.error(f"Failed to get YouTube link from: {url}")
            return None

        logger.info(f"Downloading and extracting YT transcription from: {link}")
        loader = YoutubeLoader.from_youtube_url(link, add_video_info=False)
        docs = loader.load()

        doc_parts = ""
        for doc in docs:
            doc_parts += doc.page_content

        text = doc_parts

    else:
        logger.info(f"Downloading and extracting {url.split('.')[-1]} file from: {url}")
        text = await get_content_from_url(url)

    return text
