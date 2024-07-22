import json
import os
from datetime import datetime
from io import BytesIO
from logging import getLogger
from time import time

import PyPDF2
import requests
from PyPDF2 import PdfReader
from requests import get

from src.annotations.fingerprint import fingerprint
from src.auth.schemas import UserDB
from src.chat.schemas import APIInfoBroadcastData
from src.redis import pub_sub_manager
from src.scraping.content_loaders import read_docx_from_bytes
from src.utils import get_root_path

logger = getLogger(__name__)


async def get_google_drive_file_details(
    file_id: str | int | None, user_db: UserDB
) -> dict:
    if user_db.credentials is None:
        logger.error("User credentials are missing")
        return {}
    if not file_id:
        logger.error("File ID is missing")
        return {}

    token = user_db.credentials.get("google_access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    # Get the file information
    # ------------------------
    file_info = get_google_file_info(file_id, headers)
    # ------------------------

    # Get the file content
    details: dict = {}
    mime_type = file_info.get("mimeType", "")
    if "application/pdf" in mime_type:
        details = await get_pdf_file_details(url, headers, get_urn=True)
    elif any(
        [
            "application/msword" in mime_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in mime_type,
        ]
    ):
        logger.info(f"Downloading and extracting docx file from: {url}")
        response = get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return {}
        text = read_docx_from_bytes(response.content)
        details = {
            "content": text,
        }
    elif any(
            [
                "application/vnd.google-apps.document" in mime_type,
            ]
    ):
        data = get(f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain", headers=headers)
        if data.status_code != 200:
            logger.error(f"Failed to download file: {url}")
            return {}

        text = data.text.encode("utf-8").decode("utf-8")
        details = {
            "content": text,
        }

    return {
        **details,
        "name": file_info.get("name", ""),
    }


def get_google_file_info(file_id: str | int, headers: dict) -> dict:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    file_info_response = requests.get(
        url,
        params={"fields": "*"},
        headers=headers,
    )
    if file_info_response.status_code != 200:
        logger.error(f"Failed to download file info from: {url}")
        return {}
    file_info = file_info_response.json()
    return file_info


def get_google_file_content(file_id: str, headers: dict) -> str:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    file_content_response = requests.get(url, headers=headers)
    if file_content_response.status_code != 200:
        logger.error(f"Failed to download file content from: {url}")
        return ""

    file_content = file_content_response.content
    if file_content_response.fileExtension in ["docx", "doc"]:
        file_content = read_docx_from_bytes(file_content)

    return file_content


async def get_pdf_file_details(
    url: str, headers: dict | None = None, get_urn: bool = False, room_id: str = ""
) -> dict:
    file_data_response = requests.get(url, headers=headers)
    file_data_response.raise_for_status()
    if file_data_response.status_code != 200:
        logger.error(f"Failed to download file: {url}")
        return {}

    logger.info(f"Downloaded file: {url}")
    start = time()
    # Extract the text content
    pdf_reader: PdfReader = PyPDF2.PdfReader(BytesIO(file_data_response.content))
    text_content = ""
    for page_num in range(len(pdf_reader.pages)):
        # logger.info("Extracting page: %s out of %s", page_num, len(pdf_reader.pages))
        page = pdf_reader.pages[page_num]
        extracted_page_text = page.extract_text()
        text_content += extracted_page_text + " "

    path_to_save = f"{get_root_path()}/annotations/temporary_{room_id}.pdf"
    # save the file to `path_to_save`
    with open(path_to_save, "wb") as f:
        f.write(file_data_response.content)
    logger.info(f"Extracted text content from PDF file in {time() - start}")

    if not get_urn:
        return {"content": text_content}

    # Calculate the fingerprint
    start = time()
    logger.info("Calculating the fingerprint for the PDF file")
    if room_id:
        await pub_sub_manager.publish(
            room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id,
                    date=datetime.now().isoformat(),
                    api="Fingerprint creation",
                    type="sent",
                    elapsed_time=time() - start,
                    data={
                        "url": url,
                    },
                ).model_dump(mode="json")
            ),
        )

    urn_fp = fingerprint(path_to_save)

    # urn_fp = fingerprint_pypdf2(pdf_reader)
    # urn_fp = fingerprint_fitz(path_to_save)
    # Construct the URN
    urn = f"urn:x-pdf:{urn_fp}"
    logger.info(f"Fingerprint for the PDF file: {urn} in {time() - start}")

    if room_id:
        await pub_sub_manager.publish(
            room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id,
                    date=datetime.now().isoformat(),
                    api="Fingerprint creation",
                    type="recd",
                    elapsed_time=time() - start,
                    data={
                        "urn": urn,
                    },
                ).model_dump(mode="json")
            ),
        )

    # delete the file
    os.remove(path_to_save)

    return {
        "content": text_content or "Empty PDF file.",
        "urn": urn,
    }
