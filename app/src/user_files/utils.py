from io import BytesIO
from logging import getLogger

from docx import Document
from requests import get

logger = getLogger(__name__)


def read_docx_from_bytes(content):
    try:
        doc = Document(BytesIO(content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to read docx file: {e}")
        return None


def download_and_extract_file(url: str):
    response = get(url, stream=True)
    if response.status_code != 200:
        logger.error(f"Failed to download file: {url}")
        return

    if url.endswith(".txt"):
        text = response.text
    elif url.endswith(".doc") or url.endswith(".docx"):
        text = read_docx_from_bytes(response.content)
    else:
        logger.error(f"Unsupported file type: {url}")
        return

    return text


if __name__ == "__main__":
    # Example usage
    url_txt = "https://www.gutenberg.org/files/11/11-0.txt"
    url_doc = (
        "https://hudoc.echr.coe.int/app/conversion/docx/?library=ECHR&id=001-176931",
        "&filename=CASE%20OF%20NDIDI",
        "%20v.%20THE%20UNITED%20KINGDOM.docx&logEvent=False%22,"
        "%22CASE%20OF%20NDIDI%20v.%20THE%20UNITED%20KINGDOM.docx",
    )
    a = download_and_extract_file(url_txt)
    # b = download_and_extract_file(url_doc)

    x = 10
