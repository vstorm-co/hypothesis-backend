import json
import logging

from asyncpg import InvalidTextRepresentationError
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from src.annotations.constants import TEXT_SELECTOR_PROMPT_TEMPLATE
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.config import settings
from src.constants import Environment
from src.listener.constants import listener_room_name, template_changed_info
from src.listener.schemas import WSEventMessage
from src.organizations.security import is_user_in_organization
from src.pagination_utils import enrich_paginated_items
from src.redis_client import pub_sub_manager
from src.templates.enums import VisibilityChoices
from src.templates.exceptions import (
    ForbiddenVisibilityState,
    NotValidTemplateObject,
    TemplateAlreadyExists,
    TemplateDoesNotExist,
)
from src.templates.filters import TemplateFilter, get_query_filtered_by_visibility
from src.templates.schemas import (
    AnnotationDefaultTemplate,
    TemplateCreateInput,
    TemplateCreateInputDetails,
    TemplateDB,
    TemplateDeleteOutput,
    TemplateDetails,
    TemplateUpdate,
    TemplateUpdateInputDetails,
    TemplateUpdateNameInput,
)
from src.templates.service import (
    create_template_in_db,
    delete_template_from_db,
    get_template_by_id_from_db,
    update_template_in_db,
    update_template_name_in_db,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("")
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

    query = await get_query_filtered_by_visibility(
        visibility, jwt_data.user_id, organization_uuid
    )

    filtered_query = template_filter.filter(query)
    sorted_query = template_filter.sort(filtered_query)

    # TemplateDB
    from src.database import database

    templates_db = await database.fetch_all(sorted_query)
    templates = [TemplateDB(**dict(template)) for template in templates_db]
    enrich_paginated_items(templates)

    return {
        "items": templates,
    }


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

        if settings.ENVIRONMENT != Environment.TESTING:
            await pub_sub_manager.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(
                        type=template_changed_info,
                        id=str(details.uuid),
                    ).model_dump(mode="json")
                ),
            )

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
    current_template = await get_template_by_id_from_db(template_id)
    if not current_template:
        return TemplateDoesNotExist()
    template_schema = TemplateDB(**dict(current_template))
    if (
        template_schema.visibility == VisibilityChoices.JUST_ME
        and template_schema.user_id != jwt_data.user_id
    ):
        raise TemplateDoesNotExist()

    if template_schema.organization_uuid and not await is_user_in_organization(
        jwt_data.user_id, str(template_schema.organization_uuid)
    ):
        # User is not in the organization
        # thus he cannot see the templates
        raise TemplateDoesNotExist()
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

        if settings.ENVIRONMENT != Environment.TESTING:
            await pub_sub_manager.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(
                        type=template_changed_info,
                        id=str(details.uuid),
                    ).model_dump(mode="json")
                ),
            )

        return details
    except AssertionError as e:
        logger.error(e)
        raise NotValidTemplateObject()


@router.patch("/update-name/{template_id}", response_model=TemplateDetails)
async def update_template_name(
    template_id: str,
    template_data: TemplateUpdateNameInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    template = await update_template_name_in_db(template_id, template_data)
    if not template:
        raise TemplateDoesNotExist()

    try:
        details = TemplateDetails(**dict(template))

        if settings.ENVIRONMENT != Environment.TESTING:
            await pub_sub_manager.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(
                        type=template_changed_info,
                        id=str(details.uuid),
                    ).model_dump(mode="json")
                ),
            )

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


@router.get(
    "/annotations-default-template/",
    response_model=AnnotationDefaultTemplate,
    dependencies=[Depends(parse_jwt_user_data)],
)
async def get_annotations_default_template():
    return AnnotationDefaultTemplate(
        content=TEXT_SELECTOR_PROMPT_TEMPLATE,
        arguments={
            "format_instructions": "This specify the output format of the annotation",
            "scraped_data": "Content that basing on we will create the annotations",
            "total": "Total number of splits created from the scraped data",
            "split_index": "Index of the current split",
            "prompt": "Prompt that users pass and basing on that "
            "we create the annotations",
        },
    )
