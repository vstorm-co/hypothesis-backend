class ErrorCode:
    ORGANIZATION_ALREADY_EXISTS = "Organization with this name already exists!"
    ORGANIZATION_DOES_NOT_EXIST = "Organization with this id does not exist!"
    USER_CANNOT_UPDATE_ORGANIZATION = "User cannot update organization!"
    USER_CANNOT_DELETE_ORGANIZATION = "User cannot delete organization!"
    USER_CANNOT_ADD_USER_TO_ORGANIZATION = (
        "User cannot add another user to organization!"
    )
    USER_CANNOT_DELETE_USER_FROM_ORGANIZATION = (
        "User cannot delete another user from organization!"
    )
