import hashlib
from logging import getLogger

from PyPDF2 import DocumentInformation

logger = getLogger(__name__)


def hexify(byte_string):
    logger.info(f"Hexifying {byte_string}")

    def byte_to_hex(b):
        hex_string = hex(b)

        if hex_string.startswith("0x"):
            hex_string = hex_string[2:]

        if len(hex_string) == 1:
            hex_string = "0" + hex_string

        logger.info(f"Hexified byte: {hex_string}")
        return hex_string

    return "".join([byte_to_hex(b) for b in byte_string])


def hash_of_first_kilobyte(pdf_reader):
    logger.info(f"Calculating hash of first kilobyte")
    page = pdf_reader.getPage(0)
    content = page.extractText()
    h = hashlib.md5()
    h.update(content.encode('utf-8'))
    return h.hexdigest()


def file_id_from(pdf_reader):
    logger.info(f"Extracting file id")
    trailer = pdf_reader.trailer

    try:
        id_array = trailer["/ID"]
    except KeyError:
        return None

    file_id = id_array[0]

    return hexify(file_id.encode('utf-8'))


def fingerprint_pypdf2(pdf_reader):
    return file_id_from(pdf_reader) or hash_of_first_kilobyte(pdf_reader)