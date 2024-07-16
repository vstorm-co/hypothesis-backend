import json
import os
from datetime import datetime
from io import BytesIO
from logging import getLogger
from time import time

import PyPDF2
import requests
from PyPDF2 import PdfReader

from src.annotations.fingerprint import fingerprint
from src.annotations.fingerprint_pypdf2 import fingerprint_pypdf2
from src.auth.schemas import UserDB
from src.chat.schemas import APIInfoBroadcastData
from src.redis import pub_sub_manager
from src.utils import get_root_path

logger = getLogger(__name__)


async def get_google_drive_pdf_details(
    file_id: str | int | None, user_db: UserDB
) -> dict | None:
    if user_db.credentials is None:
        logger.error("User credentials are missing")
        return None
    if not file_id:
        logger.error("File ID is missing")
        return None

    token = user_db.credentials.get("google_access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    details = await get_pdf_file_details(url, headers, get_urn=True)

    if not details:
        return None

    # Get the file information
    # ------------------------
    file_info_response = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        params={"fields": "*"},
        headers=headers,
    )
    if file_info_response.status_code != 200:
        logger.error(f"Failed to download file: {url}")
        return None
    file_info = file_info_response.json()
    # ------------------------

    return {
        "content": details["content"],
        "urn": details["urn"],
        "name": file_info.get("name", ""),
    }


async def get_pdf_file_details(
    url: str, headers: dict | None = None, get_urn: bool = False, room_id: str = ""
) -> dict | None:
    file_data_response = requests.get(url, headers=headers)
    file_data_response.raise_for_status()
    if file_data_response.status_code != 200:
        logger.error(f"Failed to download file: {url}")
        return None

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

    # import pdfminer.pdfdocument
    # import pdfminer.pdfparser
    # parser = pdfminer.pdfparser.PDFParser(open(path_to_save, "rb"))
    # document = pdfminer.pdfdocument.PDFDocument(parser)
    # urn_fp = fingerprint(document)

    urn_fp = fingerprint_pypdf2(pdf_reader)
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
        "content": text_content,
        "urn": urn,
    }
