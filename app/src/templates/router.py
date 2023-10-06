from asyncpg import InvalidTextRepresentationError
from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.templates import service
from src.templates.exceptions import (
    ForbiddenVisibilityState,
    TemplateAlreadyExists,
    TemplateDoesNotExist,
)
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

router = APIRouter()


@router.get("", response_model=Page[TemplateDB])
async def get_templates(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    template_query = service.get_templates_query(jwt_data.user_id)
    paginated_templates = await paginate_templates(template_query)

    if not paginated_templates:
        return []

    return paginated_templates


@router.get("/{template_id}", response_model=TemplateDetails)
async def get_template_with_content(
    template_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    template = await service.get_template_by_id_from_db(template_id)

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
    template = await service.create_template_in_db(template_input_data)

    if not template:
        raise TemplateAlreadyExists()

    return TemplateDetails(**dict(template))


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
        template = await service.update_template_in_db(template_update_details)
    except InvalidTextRepresentationError:
        raise ForbiddenVisibilityState()

    if not template:
        raise TemplateDoesNotExist()

    return TemplateDetails(**dict(template))


@router.delete("/{template_id}", response_model=TemplateDeleteOutput)
async def delete_template(
    template_id: str,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    await service.delete_template_from_db(template_id, jwt_data.user_id)

    return TemplateDeleteOutput(status="success")
