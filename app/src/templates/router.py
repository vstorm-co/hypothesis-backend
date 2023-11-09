import logging

from asyncpg import InvalidTextRepresentationError
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from fastapi_pagination import Page

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.datetime_utils import aware_datetime_fields
from src.organizations.security import is_user_in_organization
from src.templates.exceptions import (
    ForbiddenVisibilityState,
    NotValidTemplateObject,
    TemplateAlreadyExists,
    TemplateDoesNotExist,
)
from src.templates.filters import TemplateFilter, get_query_filtered_by_visibility
from src.templates.pagination import paginate_templates
from src.templates.schemas import (
    TemplateCreateInput,
    TemplateCreateInputDetails,
    TemplateDB,
    TemplateDeleteOutput,
    TemplateDetails,
    TemplateUpdate,
    TemplateUpdateInputDetails,
)
from src.templates.service import (
    create_template_in_db,
    delete_template_from_db,
    get_template_by_id_from_db,
    update_template_in_db,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("", response_model=Page[TemplateDB])
async def get_templates(
    visibility: str | None = None,
    organization_uuid: str | None = None,
    template_filter: TemplateFilter = FilterDepends(TemplateFilter),
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if organization_uuid and not await is_user_in_organization(
        jwt_data.user_id, str(organization_uuid)
    ):
        # User is not in the organization
        # thus he cannot see the rooms
        raise TemplateDoesNotExist()

    query = get_query_filtered_by_visibility(
        visibility, jwt_data.user_id, organization_uuid
    )

    filtered_query = template_filter.filter(query)
    sorted_query = template_filter.sort(filtered_query)

    templates = await paginate_templates(sorted_query)
    aware_datetime_fields(templates.items)

    return templates


@router.get("/{template_id}", response_model=TemplateDetails)
async def get_template_with_content(
    template_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    template = await get_template_by_id_from_db(template_id)

    if not template:
        raise TemplateDoesNotExist()

    return TemplateDetails(**dict(template))


@router.post("", response_model=TemplateDetails)
async def create_template(
    template_data: TemplateCreateInput, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    template_input_data = TemplateCreateInputDetails(
        **template_data.model_dump(), user_id=jwt_data.user_id
    )
    template = await create_template_in_db(template_input_data)

    if not template:
        raise TemplateAlreadyExists()

    try:
        details = TemplateDetails(**dict(template))
        return details
    except AssertionError as e:
        logger.error(e)
        raise NotValidTemplateObject()


@router.patch("/{template_id}", response_model=TemplateDetails)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    try:
        template_update_details = TemplateUpdateInputDetails(
            **template_data.model_dump(),
            uuid=template_id,
            user_id=jwt_data.user_id,
        )
        template = await update_template_in_db(template_update_details)
    except InvalidTextRepresentationError:
        raise ForbiddenVisibilityState()

    if not template:
        raise TemplateDoesNotExist()

    try:
        details = TemplateDetails(**dict(template))
        return details
    except AssertionError as e:
        logger.error(e)
        raise NotValidTemplateObject()


@router.delete("/{template_id}", response_model=TemplateDeleteOutput)
async def delete_template(
    template_id: str,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    await delete_template_from_db(template_id, jwt_data.user_id)

    return TemplateDeleteOutput(status="success")
