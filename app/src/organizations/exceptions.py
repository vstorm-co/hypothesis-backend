from src.exceptions import BadRequest, NotFound, PermissionDenied
from src.organizations.constants import ErrorCode


class OrganizationAlreadyExists(BadRequest):
    DETAIL = ErrorCode.ORGANIZATION_ALREADY_EXISTS


class OrganizationDoesNotExist(NotFound):
    DETAIL = ErrorCode.ORGANIZATION_DOES_NOT_EXIST


class UserCannotUpdateOrganization(PermissionDenied):
    DETAIL = ErrorCode.USER_CANNOT_UPDATE_ORGANIZATION


class UserCannotDeleteOrganization(PermissionDenied):
    DETAIL = ErrorCode.USER_CANNOT_DELETE_ORGANIZATION


class UserCannotAddUserToOrganization(PermissionDenied):
    DETAIL = ErrorCode.USER_CANNOT_ADD_USER_TO_ORGANIZATION


class UserCannotDeleteUserFromOrganization(PermissionDenied):
    DETAIL = ErrorCode.USER_CANNOT_DELETE_USER_FROM_ORGANIZATION
