import os
from io import BytesIO
from logging import getLogger

import PyPDF2
import requests
from PyPDF2 import PdfReader

from src.annotations.fingerprint import fingerprint
from src.auth.schemas import UserDB
from src.utils import get_root_path

logger = getLogger(__name__)


async def get_pdf_file_details(file_id: str | int, user_db: UserDB) -> dict | None:
    if user_db.credentials is None:
        logger.error("User credentials are missing")
        return None
    token = user_db.credentials.get("google_access_token", "")

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    headers = {"Authorization": f"Bearer {token}"}
    # Get the file information
    # ------------------------
    file_info_response = requests.get(url, params={"fields": "*"}, headers=headers)
    if file_info_response.status_code != 200:
        logger.error(f"Failed to download file: {url}")
        return None
    file_info = file_info_response.json()
    # ------------------------

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    file_data_response = requests.get(url, headers=headers)
    if file_data_response.status_code != 200:
        logger.error(f"Failed to download file: {url}")
        return None

    logger.info(f"Downloaded file: {url}")
    # Extract the text content
    pdf_reader: PdfReader = PyPDF2.PdfReader(BytesIO(file_data_response.content))
    text_content = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text_content += page.extract_text()

    path_to_save = f"{get_root_path()}/annotations/{file_info.get('name')}"
    # save the file to `path_to_save`
    with open(path_to_save, "wb") as f:
        f.write(file_data_response.content)

    logger.info(f"Extracted text content from PDF file: {text_content[:10]}...")
    # Calculate the fingerprint
    urn_fp = fingerprint(path_to_save)

    # Construct the URN
    urn = f"urn:x-pdf:{urn_fp}"
    logger.info(f"URN for the PDF file: {urn}")

    # delete the file
    os.remove(path_to_save)

    return {
        "content": text_content,
        "urn": urn,
    }
