import logging

logger = logging.getLogger(__name__)


def validate_data_tags(tags: list[str] | None) -> list[str] | None:
    logger.info(f"Validating tags: {tags}")
    if not tags:
        return None

    if all([not tag for tag in tags]):
        return None

    return tags
