from src.chat.constants import ErrorCode
from src.exceptions import BadRequest


class RoomAlreadyExists(BadRequest):
    DETAIL = ErrorCode.ROOM_ALREADY_EXISTS


class RoomDoesNotExist(BadRequest):
    DETAIL = ErrorCode.ROOM_DOES_NOT_EXIST
