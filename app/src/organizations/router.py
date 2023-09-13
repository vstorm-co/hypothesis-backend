import logging

from fastapi import APIRouter, Depends
from starlette import status

from src.auth.jwt import parse_jwt_admin_data, parse_jwt_user_data
from src.auth.schemas import JWTData
from src.organizations.exceptions import (
    OrganizationAlreadyExists,
    OrganizationDoesNotExist,
)
from src.organizations.schemas import (
    OrganizationCreate,
    OrganizationDB,
    OrganizationDeleteOutput,
    SetUserOrganizationInput,
    SetUserOrganizationOutput, OrganizationUpdate,
)
from src.organizations.service import get_organizations_from_db, get_user_organization_by_id_from_db, \
    create_organization_in_db, set_user_organization_in_db, update_organization_in_db, delete_organization_from_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[OrganizationDB])
async def get_organizations(jwt_data: JWTData = Depends(parse_jwt_admin_data)):
    organizations = await get_organizations_from_db()

    if not organizations:
        return []

    return [OrganizationDB(**dict(organization)) for organization in organizations]


@router.get("/{organization_uuid}", response_model=OrganizationDB)
async def get_organization_by_id(
    organization_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    organization = await get_user_organization_by_id_from_db(
        organization_uuid, jwt_data.user_id
    )

    if not organization:
        raise OrganizationDoesNotExist()

    return OrganizationDB(**dict(organization))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrganizationDB)
async def create_organization(
    organization_data: OrganizationCreate,
    jwt_data: JWTData = Depends(parse_jwt_admin_data),
):
    organization = await create_organization_in_db(organization_data)
    if not organization:
        raise OrganizationAlreadyExists()

    return OrganizationDB(**dict(organization))


@router.put("/{organization_uuid}", response_model=OrganizationDB)
async def update_organization(
    organization_uuid: str,
    organization_data: OrganizationUpdate,
    jwt_data: JWTData = Depends(parse_jwt_admin_data),
):
    organization = await update_organization_in_db(organization_uuid, organization_data)
    if not organization:
        raise OrganizationDoesNotExist()

    return OrganizationDB(**dict(organization))


@router.delete("/{organization_uuid}", response_model=OrganizationDeleteOutput)
async def delete_organization(
    organization_uuid: str,
    jwt_data: JWTData = Depends(parse_jwt_admin_data),
):
    org = await delete_organization_from_db(organization_uuid)
    if not org:
        raise OrganizationDoesNotExist()

    return OrganizationDeleteOutput(status="Deleted")


@router.post("/set-user-organization", response_model=SetUserOrganizationOutput)
async def add_user_to_organization(
    data: SetUserOrganizationInput, jwt_data: JWTData = Depends(parse_jwt_admin_data)
):
    result = await set_user_organization_in_db(
        data.organization_uuid, data.user_id
    )
    if not result:
        raise OrganizationDoesNotExist()

    return SetUserOrganizationOutput(status="User organization set")
