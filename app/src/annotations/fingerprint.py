import hashlib
import logging

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser

logger = logging.getLogger(__name__)


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
    with open(path, "rb") as f:
        parser = PDFParser(f)
        document = PDFDocument(parser)

        logger.info(f"Document xrefs: {document.xrefs} (len {len(document.xrefs)})")
        for xref in document.xrefs:
            logger.info(f"Xref: {xref}")
            trailer = xref.get_trailer()
            logger.info(f"Trailer: {trailer}")
            try:
                id_array = trailer["ID"]
            except KeyError:
                continue

            # Resolve indirect object references.
            try:
                id_array = id_array.resolve()
            except AttributeError:
                pass

            try:
                file_id = id_array[0]
            except TypeError:
                continue

            return hexify(file_id)


def fingerprint(path):
    return file_id_from(path) or hash_of_first_kilobyte(path)
