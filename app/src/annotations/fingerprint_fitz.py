import hashlib
from logging import getLogger
import fitz  # PyMuPDF

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


def hash_of_first_kilobyte(path):
    logger.info(f"Calculating hash of first kilobyte of {path}")
    with open(path, "rb") as f:
        h = hashlib.md5()
        h.update(f.read(1024))
        return h.hexdigest()


def file_id_from(path):
    """
    Return the PDF file identifier from the given file as a hex string.
    Returns None if the document doesn't contain a file identifier.
    """
    logger.info(f"Extracting file id from {path}")
    doc = fitz.open(path)

    try:
        id_array = doc.metadata["id"]
        logger.info(f"ID array: {id_array}")
        if id_array:
            # ID is typically in the form (OriginalID, ModifiedID)
            file_id = id_array[0]
            return hexify(file_id.encode('utf-8'))
    except KeyError:
        logger.info("No file identifier found")
        return None


def fingerprint_fitz(path):
    return file_id_from(path) or hash_of_first_kilobyte(path)
