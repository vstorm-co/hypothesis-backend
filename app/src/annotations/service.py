import logging

from src.annotations.hypothesis_api import get_hypothesis_annotation_by_id
from src.annotations.messaging import create_message_for_users
from src.annotations.schemas import HypothesisAnnotationCreateOutput
from src.chat.schemas import MessageDBWithTokenUsage

logger = logging.getLogger(__name__)


async def check_for_annotation_message_type(
    messages_schema: list[MessageDBWithTokenUsage],
) -> list[MessageDBWithTokenUsage]:
    for index, message in enumerate(messages_schema):
        if message.created_by == "annotation":
            annotations: list[HypothesisAnnotationCreateOutput] = []
            for annotation_id in message.content.split(","):
                annotation: HypothesisAnnotationCreateOutput | None = (
                    get_hypothesis_annotation_by_id(
                        annotation_id,
                        message.content_dict["api_key"]
                        if message.content_dict
                        else None,
                    )
                )
                if annotation:
                    annotations.append(annotation)
            if not annotations:
                if message.content == "Creating...":
                    messages_schema[index].content = ""
                    messages_schema[index].content_html = None
                    continue
                messages_schema[index].content = "No annotations created"
                messages_schema[index].content_html = None
                continue

            messages_schema[index].content = create_message_for_users(
                annotations,
                message,
            )
            if not annotations[0].links:
                continue

            # get link to the very first annotation
            messages_schema[index].content_html = annotations[0].links.get(
                "incontext", ""
            )

    return messages_schema
