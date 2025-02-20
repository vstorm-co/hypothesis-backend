import logging
import os

from fastapi import APIRouter, Depends, UploadFile
from starlette import status

from src.auth.exceptions import UserNotFound
from src.auth.jwt import parse_jwt_admin_data, parse_jwt_user_data
from src.auth.schemas import JWTData, UserDBNoSecrets
from src.auth.service import get_user_by_id
from src.config import settings
from src.organizations.exceptions import (
    OrganizationAlreadyExists,
    OrganizationDoesNotExist,
    UserCannotAddUserToOrganization,
    UserCannotDeleteOrganization,
    UserCannotDeleteUserFromOrganization,
    UserCannotUpdateOrganization,
)
from src.organizations.schemas import (
    AddNewUsersToOrganizationInput,
    AddUsersToOrganizationInput,
    AddUsersToOrganizationOutput,
    AddUserToOrganizationByEmails,
    OrganizationBase,
    OrganizationCreate,
    OrganizationCreateDetails,
    OrganizationDB,
    OrganizationDeleteOutput,
    OrganizationDetails,
    OrganizationPictureUpdate,
    OrganizationUpdate,
    RemoveUsersFromOrganizationInput,
    RemoveUsersFromOrganizationOutput,
)
from src.organizations.security import (
    check_admin_count_before_deletion,
    check_user_count_before_deletion,
    is_user_in_organization,
    is_user_organization_admin,
)
from src.organizations.service import (
    add_admins_to_organization_in_db,
    add_users_to_organization_in_db,
    add_users_to_organization_in_db_by_emails,
    create_organization_in_db,
    delete_admins_from_organization_in_db,
    delete_organization_from_db,
    delete_users_from_organization_in_db,
    get_admins_from_organization_by_id_from_db,
    get_organization_by_id_from_db,
    get_organizations_by_user_id_from_db,
    get_organizations_from_db,
    get_organizations_from_db_by_domain,
    get_users_from_organization_by_id_from_db,
    remove_all_admins_from_organization_in_db,
    remove_all_users_from_organization_in_db,
    update_organization_in_db,
    update_organization_picture,
)
from src.organizations.utils import save_picture

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[OrganizationDB])
async def get_organizations(jwt_data: JWTData = Depends(parse_jwt_admin_data)):
    organizations = await get_organizations_from_db()

    if not organizations:
        return []

    return [OrganizationDB(**dict(organization)) for organization in organizations]


# Temporary function
@router.get("/domain-organizations", response_model=list[OrganizationDB])
async def get_organizations_by_domain(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    user = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise UserNotFound()
    user_email = user["email"]
    user_domain = user_email.split("@")[1]
    organizations = await get_organizations_from_db_by_domain(user_domain)

    if not organizations:
        return []

    return [OrganizationDB(**dict(organization)) for organization in organizations]


# Temporary function
@router.post(
    "/add-user/{organization_uuid}", response_model=AddUsersToOrganizationOutput
)
async def add_user(
    organization_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    await add_users_to_organization_in_db(organization_uuid, [jwt_data.user_id])

    return AddUsersToOrganizationOutput(status="Users added to the organization")


@router.post(
    "/add-users/{organization_uuid}", response_model=AddUsersToOrganizationOutput
)
async def add_users_by_emails(
    organization_uuid: str,
    users_data: AddUserToOrganizationByEmails,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    # check if user is an admin of the organization
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotAddUserToOrganization()

    users_status = await add_users_to_organization_in_db_by_emails(
        organization_uuid, users_data.emails, users_data.as_admin
    )

    return AddUsersToOrganizationOutput(status=users_status)


@router.get("/user-organizations", response_model=list[OrganizationDB])
async def get_user_organizations(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    organizations = await get_organizations_by_user_id_from_db(jwt_data.user_id)

    if not organizations:
        return []

    return [OrganizationDB(**dict(organization)) for organization in organizations]


@router.get("/{organization_uuid}", response_model=OrganizationDetails)
async def get_organization_by_id(
    organization_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    if not await is_user_in_organization(jwt_data.user_id, organization_uuid):
        raise OrganizationDoesNotExist()

    organization = await get_organization_by_id_from_db(organization_uuid)

    if not organization:
        raise OrganizationDoesNotExist()

    # Get users and admins
    users = await get_users_from_organization_by_id_from_db(organization_uuid)
    admins = await get_admins_from_organization_by_id_from_db(organization_uuid)

    # Convert users and admins to dictionaries for easier processing
    if not users:
        users = []
    if not admins:
        admins = []

    users_dict = {user["id"]: UserDBNoSecrets(**dict(user)) for user in users}
    admins_id_set = {admin["id"] for admin in admins}

    # Mark users as admins if they are in the admins set
    for user in users_dict.values():
        user.is_admin = user.id in admins_id_set

    return OrganizationDetails(
        **dict(organization),
        users=list(users_dict.values()),
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrganizationDB)
async def create_organization(
    organization_data: OrganizationCreate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    # Temporary
    user = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise UserNotFound()
    user_email = user["email"]
    user_domain = user_email.split("@")[1]
    organization_data_details = OrganizationCreateDetails(
        **organization_data.model_dump()
    )
    if user_domain:
        organization_data_details.domain = user_domain
    organization = await create_organization_in_db(organization_data_details)

    if not organization:
        raise OrganizationAlreadyExists()

    # add user as a member of the organization and as an admin
    logger.info("Adding user to the organization...")
    await add_users_to_organization_in_db(organization["uuid"], [jwt_data.user_id])
    logger.info("User added to the organization")

    logger.info("Adding user as admin to the organization...")
    await add_admins_to_organization_in_db(organization["uuid"], [jwt_data.user_id])
    logger.info("User added as admin to the organization")

    return OrganizationDB(**dict(organization))


@router.put("/{organization_uuid}", response_model=OrganizationDB)
async def update_organization(
    organization_uuid: str,
    organization_data: OrganizationUpdate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotUpdateOrganization()
    organization = await update_organization_in_db(organization_uuid, organization_data)
    if not organization:
        raise OrganizationDoesNotExist()

    return OrganizationDB(**dict(organization))


@router.post("/set-image/{organization_uuid}", response_model=OrganizationDB)
async def set_organization_image(
    organization_uuid: str,
    picture: UploadFile,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotUpdateOrganization()
    organization = await get_organization_by_id_from_db(organization_uuid)
    if not organization:
        raise OrganizationDoesNotExist
    organization_base = OrganizationBase(**dict(organization))
    dir_name = organization_base.name
    dir_path = os.path.join(settings.MEDIA_DIR, dir_name)
    await save_picture(picture, dir_path)
    organization_data = OrganizationPictureUpdate(
        picture=dir_path + f"/{picture.filename}"
    )
    updated_organization = await update_organization_picture(
        organization_uuid, organization_data
    )

    return OrganizationDB(**dict(updated_organization))


@router.delete("/{organization_uuid}", response_model=OrganizationDeleteOutput)
async def delete_organization(
    organization_uuid: str,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotDeleteOrganization()

    # make sure to delete all users from the organization
    logger.info("Deleting all users from the organization...")
    await remove_all_users_from_organization_in_db(organization_uuid)
    logger.info("Users deleted from the organization")

    # make sure to delete all admins from the organization
    logger.info("Deleting all admins from the organization...")
    await remove_all_admins_from_organization_in_db(organization_uuid)
    logger.info("Admins deleted from the organization")

    org = await delete_organization_from_db(organization_uuid)
    if not org:
        raise OrganizationDoesNotExist()

    return OrganizationDeleteOutput(status="Organization deleted")


@router.post(
    "/add-organization-permissions/{organization_uuid}",
    response_model=AddUsersToOrganizationOutput,
)
async def add_user_permissions_to_organization(
    organization_uuid: str,
    data: AddUsersToOrganizationInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotAddUserToOrganization()

    if data.user_ids:
        logger.info("Adding users to the organization...")
        await add_users_to_organization_in_db(organization_uuid, data.user_ids)
        logger.info("Users added to the organization")

    if data.admin_ids:
        logger.info("Adding admins to the organization...")
        await add_admins_to_organization_in_db(organization_uuid, data.admin_ids)
        logger.info("Admins added to the organization")

    return AddUsersToOrganizationOutput(status="Users added to the organization")


@router.post(
    "/add-new-users/{organization_uuid}",
    response_model=AddUsersToOrganizationOutput,
)
async def add_new_users_to_organization(
    organization_uuid: str,
    data: AddNewUsersToOrganizationInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    # check if user is an admin of the organization
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotAddUserToOrganization()

    users_status = await add_users_to_organization_in_db_by_emails(
        organization_uuid, data.user_ids or data.admin_ids, bool(data.admin_ids)
    )

    return AddUsersToOrganizationOutput(status=users_status)


@router.post(
    "/revoke-organization-permissions/{organization_uuid}",
    response_model=RemoveUsersFromOrganizationOutput,
)
async def revoke_user_permissions_from_organization(
    organization_uuid: str,
    data: RemoveUsersFromOrganizationInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotDeleteUserFromOrganization()

    if not await check_user_count_before_deletion(organization_uuid, data.user_ids):
        raise UserCannotDeleteUserFromOrganization()

    if not await check_admin_count_before_deletion(organization_uuid, data.admin_ids):
        raise UserCannotDeleteUserFromOrganization()

    if data.user_ids:
        logger.info("Deleting users from the organization...")
        await delete_users_from_organization_in_db(organization_uuid, data.user_ids)
        logger.info("Users deleted from the organization")

    if data.admin_ids:
        logger.info("Deleting admins from the organization...")
        await delete_admins_from_organization_in_db(organization_uuid, data.admin_ids)
        logger.info("Admins deleted from the organization")

    return RemoveUsersFromOrganizationOutput(
        status="Users removed from the organization"
    )
