from src.exceptions import BadRequest, NotFound
from src.organizations.constants import ErrorCode


class OrganizationAlreadyExists(BadRequest):
    DETAIL = ErrorCode.ORGANIZATION_ALREADY_EXISTS


class OrganizationDoesNotExist(NotFound):
    DETAIL = ErrorCode.ORGANIZATION_DOES_NOT_EXIST
