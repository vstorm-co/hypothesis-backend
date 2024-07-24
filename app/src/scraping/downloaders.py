import asyncio
from logging import getLogger

from langchain_community.document_loaders import YoutubeLoader
from requests import get, head

from src.google_drive.downloader import get_pdf_file_details
from src.scraping.content_loaders import get_content_from_url, read_docx_from_bytes
from src.youtube.service import YouTubeService

logger = getLogger(__name__)

youtube_service: YouTubeService = YouTubeService()


async def download_and_extract_content_from_url(
    url: str, get_urn: bool = False, room_id: str = ""
) -> dict | None:
    logger.info(f"Checking content type of: {url}")
    response = head(url, allow_redirects=True, stream=True)
    content_type = response.headers.get("Content-Type", "")
    logger.info(f"Content type of {url}: {content_type}")

    if "text/plain" in content_type:
        logger.info(f"Downloading and extracting txt file from: {url}")
        response = get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return None

        return {
            "content": response.text,
            "content_type": "text/plain",
        }
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
        return {
            "content": text,
            "content_type": "application/msword",
        }
    elif "application/pdf" in content_type:
        logger.info(f"Downloading and extracting pdf file from: {url}")
        details = await get_pdf_file_details(url=url, get_urn=get_urn, room_id=room_id)
        if not details:
            logger.error(f"Failed to download file: {url}")
            # return "Empty PDF file."
            return {
                "content": "Empty PDF file.",
                "content_type": "application/pdf",
            }

        text = details.get("content", "")
        return {
            "content": text,
            "content_type": "application/pdf",
            "urn": details.get("urn", ""),
        }
    elif any(substring in url for substring in ["youtube", "youtu.be", "you.tube"]):
        link: str | None = youtube_service.get_youtube_link(url)
        if not link:
            logger.error(f"Failed to get YouTube link from: {url}")
            return None

        logger.info(f"Downloading and extracting YT transcription from: {link}")
        loader = YoutubeLoader.from_youtube_url(link, add_video_info=False)

        try:
            docs = await loader.aload()
            doc_parts = ""

            tries = 1
            while not docs and tries <= 5:
                logger.info(f"Failed to download YT transcription from: {link}, retrying... {tries}/5")
                docs = await loader.aload()
                tries += 1

            for doc in docs:
                doc_parts += doc.page_content

            logger.info(f"Extracted YT transcription from: {link}, {len(doc_parts)} chars.")
            return {
                "content": doc_parts,
                "content_type": "youtube_transcription",
            }
        except Exception:
            logger.error(
                f"Failed to download and extract YT transcription from: {link}"
            )
            return None

    logger.info(f"Downloading and extracting {url.split('.')[-1]} file from: {url}")
    text = await get_content_from_url(url)

    return {
        "content": text,
        "content_type": url.split(".")[-1],
    }


async def main():
    url = "https://arxiv.org/pdf/2406.06326"
    url_data = await download_and_extract_content_from_url(url, get_urn=True)
    print(url_data)


if __name__ == "__main__":
    asyncio.run(main())
