from src.exceptions import BadRequest
from src.organizations.constants import ErrorCode


class TeamAlreadyExists(BadRequest):
    DETAIL = ErrorCode.ORGANIZATION_ALREADY_EXISTS


class TeamDoesNotExist(BadRequest):
    DETAIL = ErrorCode.ORGANIZATION_DOES_NOT_EXIST
