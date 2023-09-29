import logging

from fastapi import APIRouter, Depends, UploadFile
from starlette import status

from src.auth.exceptions import UserNotFound
from src.auth.jwt import parse_jwt_admin_data, parse_jwt_user_data
from src.auth.schemas import JWTData, UserDB
from src.auth.service import get_user_by_id
from src.organizations.exceptions import (
    OrganizationDoesNotExist,
    UserCannotAddUserToOrganization,
    UserCannotDeleteOrganization,
    UserCannotDeleteUserFromOrganization,
    UserCannotUpdateOrganization,
)
from src.organizations.schemas import (
    AddUsersToOrganizationInput,
    AddUsersToOrganizationOutput,
    OrganizationCreate,
    OrganizationDB,
    OrganizationDeleteOutput,
    OrganizationDetails,
    OrganizationUpdate,
    RemoveUsersFromOrganizationInput,
    RemoveUsersFromOrganizationOutput,
)
from src.organizations.security import (
    check_admin_user_count_before_deletion,
    is_user_organization_admin,
)
from src.organizations.service import (
    add_admins_to_organization_in_db,
    add_users_to_organization_in_db,
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
)

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
@router.post("/add-user", response_model=AddUsersToOrganizationOutput)
async def add_user(
    data: AddUsersToOrganizationInput, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    await add_users_to_organization_in_db(data.organization_uuid, [jwt_data.user_id])

    return AddUsersToOrganizationOutput(status="Users added to the organization")


@router.get("/user-organizations", response_model=list[OrganizationDB])
async def get_user_organizations(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    organizations = await get_organizations_by_user_id_from_db(jwt_data.user_id)

    if not organizations:
        return []

    return [OrganizationDB(**dict(organization)) for organization in organizations]


@router.get("/{organization_uuid}", response_model=OrganizationDB)
async def get_organization_by_id(
    organization_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise OrganizationDoesNotExist()

    organization = await get_organization_by_id_from_db(
        organization_uuid, jwt_data.user_id
    )

    if not organization:
        raise OrganizationDoesNotExist()

    # get organization users
    users_list = []
    users = await get_users_from_organization_by_id_from_db(organization_uuid)
    if users:
        users_list = [UserDB(**dict(user)) for user in users]

    # get organization admins
    admins_list = []
    admins = await get_admins_from_organization_by_id_from_db(organization_uuid)
    if admins:
        admins_list = [UserDB(**dict(admin)) for admin in admins]

    return OrganizationDetails(
        **dict(organization),
        users=users_list,
        admins=admins_list,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_data: OrganizationCreate,
    file: UploadFile,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    print("\n\n\n\naaaa")
    print(organization_data.file.filename)
    # Temporary
    # user = await get_user_by_id(jwt_data.user_id)
    # if not user:
    #     raise UserNotFound()
    # user_email = user["email"]
    # user_domain = user_email.split("@")[1]
    return {"answer": "Ok"}
    # organization_data_details = OrganizationCreateDetails(
    #     **organization_data.model_dump()
    # )
    # if user_domain:
    #     organization_data_details.domain = user_domain
    # async with aiofiles.open('logo.png', 'wb') as out_file:
    #     content = await file.read()
    #     await out_file.write(content)
    #     organization_data_details.picture = out_file.name
    # organization = await create_organization_in_db(organization_data_details)
    #
    # if not organization:
    #     raise OrganizationAlreadyExists()
    #
    # # add user as a member of the organization and as an admin
    # logger.info("Adding user to the organization...")
    # await add_users_to_organization_in_db(organization["uuid"], [jwt_data.user_id])
    # logger.info("User added to the organization")
    #
    # logger.info("Adding user as admin to the organization...")
    # await add_admins_to_organization_in_db(organization["uuid"], [jwt_data.user_id])
    # logger.info("User added as admin to the organization")
    #
    # return OrganizationDB(**dict(organization))


@router.put("/{organization_uuid}", response_model=OrganizationDB)
async def update_organization(
    organization_uuid: str,
    organization_data: OrganizationUpdate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotUpdateOrganization()

    organization = await update_organization_in_db(
        organization_uuid, jwt_data.user_id, organization_data
    )
    if not organization:
        raise OrganizationDoesNotExist()

    return OrganizationDB(**dict(organization))


@router.delete("/{organization_uuid}", response_model=OrganizationDeleteOutput)
async def delete_organization(
    organization_uuid: str,
    jwt_data: JWTData = Depends(parse_jwt_admin_data),
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


@router.post("/add-users-to-organization", response_model=AddUsersToOrganizationOutput)
async def add_user_to_organization(
    data: AddUsersToOrganizationInput, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    if not await is_user_organization_admin(jwt_data.user_id, data.organization_uuid):
        raise UserCannotAddUserToOrganization()

    if data.user_ids:
        logger.info("Adding users to the organization...")
        await add_users_to_organization_in_db(data.organization_uuid, data.user_ids)
        logger.info("Users added to the organization")

    if data.admin_ids:
        logger.info("Adding admins to the organization...")
        await add_admins_to_organization_in_db(data.organization_uuid, data.admin_ids)
        logger.info("Admins added to the organization")

    return AddUsersToOrganizationOutput(status="Users added to the organization")


@router.delete(
    "/delete-users-from-organization/{organization_uuid}",
    response_model=RemoveUsersFromOrganizationOutput,
)
async def delete_user_from_organization(
    organization_uuid: str,
    data: RemoveUsersFromOrganizationInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not await is_user_organization_admin(jwt_data.user_id, organization_uuid):
        raise UserCannotDeleteUserFromOrganization()

    if not check_admin_user_count_before_deletion(
        organization_uuid, data.user_ids or [], data.admin_ids or []
    ):
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
