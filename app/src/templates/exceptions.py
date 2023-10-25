from src.exceptions import BadRequest, NotFound
from src.templates.constants import ErrorCode


class TemplateAlreadyExists(BadRequest):
    DETAIL = ErrorCode.TEMPLATE_ALREADY_EXISTS


class TemplateDoesNotExist(NotFound):
    DETAIL = ErrorCode.TEMPLATE_DOES_NOT_EXIST


class TemplateIsNotShared(BadRequest):
    DETAIL = ErrorCode.TEMPLATE_IS_NOT_SHARED


class ForbiddenVisibilityState(BadRequest):
    DETAIL = ErrorCode.FORBIDDEN_VISIBILITY_STATE


class NotValidTemplateObject(BadRequest):
    DETAIL = ErrorCode.NOT_VALID_TEMPLATE_OBJECT
