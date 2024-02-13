from src.exceptions import BadRequest, NotFound
from src.user_files.constants import ErrorCode


class UserFileDoesNotExist(NotFound):
    DETAIL = ErrorCode.USER_FILE_DOES_NOT_EXIST


class UserFileAlreadyExists(BadRequest):
    DETAIL = ErrorCode.USER_FILE_ALREADY_EXISTS


class FailedToDownloadAndExtractFile(BadRequest):
    DETAIL = ErrorCode.FAILED_TO_DOWNLOAD_AND_EXTRACT_FILE
