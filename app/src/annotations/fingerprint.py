import hashlib
from logging import getLogger

import pdfminer.pdfdocument
import pdfminer.pdfparser

"""
Source:
https://www.seanh.cc/2017/11/22/pdf-fingerprinting/#pdf-fingerprinting-in-python
"""

logger = getLogger(__name__)


def hexify(byte_string):
    # ba = [ord(c) for c in byte_string]  #bytearray(byte_string)
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
    f = open(path, "rb")
    h = hashlib.md5()
    h.update(f.read(1024))
    return h.hexdigest()


def file_id_from(path):
    """
    Return the PDF file identifier from the given file as a hex string.
    Returns None if the document doesn't contain a file identifier.
    """
    logger.info(f"Extracting file id from {path}")
    parser = pdfminer.pdfparser.PDFParser(open(path, "rb"))
    document = pdfminer.pdfdocument.PDFDocument(parser)

    logger.info(f"Document xrefs: {document.xrefs} (len {len(document.xrefs)})")
    for xref in document.xrefs:
        logger.info(f"Xref: {xref}")
        if xref.trailer:
            trailer = xref.trailer

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
