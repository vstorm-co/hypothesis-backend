from fastapi import APIRouter, Depends
from starlette import status

from src.auth.jwt import parse_jwt_user_data, validate_admin_access
from src.auth.schemas import JWTData
from src.organizations import service
from src.organizations.exceptions import TeamAlreadyExists, TeamDoesNotExist
from src.organizations.schemas import (
    AddUserInput,
    AddUserOutput,
    OrganizationBase,
    OrganizationChange,
    OrganizationCreate,
    OrganizationDB,
    OrganizationDelete,
    OrganizationDeleteOutput,
)

router = APIRouter()


@router.get("", response_model=list[OrganizationDB])
async def get_organizations(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    organizations = await service.get_organizations_from_db(jwt_data.user_id)

    if not organizations:
        return []

    return [OrganizationDB(**dict(organization)) for organization in organizations]


@router.get("/{organization_uuid}")
async def get_organization_by_id(
    organization_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    organization = await service.get_organization_by_id_from_db(organization_uuid)

    if not organization:
        return []

    return organization


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_data: OrganizationCreate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    await validate_admin_access(jwt_data)
    organization = await service.create_organization_in_db(organization_data)

    if not organization:
        raise TeamAlreadyExists()

    return organization


@router.put("/{organization_uuid}", response_model=OrganizationDB)
async def update_organization_in_db(
    organization_uuid: str,
    organization_data: OrganizationBase,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    await validate_admin_access(jwt_data)
    organization_with_uuid = OrganizationChange(
        **organization_data.model_dump(), organization_uuid=organization_uuid
    )
    organization = await service.update_organization_in_db(organization_with_uuid)

    if not organization:
        raise TeamDoesNotExist()

    return organization


@router.delete("/{organization_uuid}", response_model=OrganizationDeleteOutput)
async def delete_organization_from_db(
    organization_uuid: str,
    organization_data: OrganizationBase,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    organization_data_with_uuid = OrganizationDelete(
        **organization_data.model_dump(), organization_uuid=organization_uuid
    )
    await service.delete_organization_from_db(organization_data_with_uuid)

    return OrganizationDeleteOutput(status="Ok")


@router.post("add-user-to-organization", response_model=AddUserOutput)
async def add_user_to_organization(
    data: AddUserInput, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    await service.add_user_to_organization_in_db(data)

    return AddUserOutput(status="Ok")
