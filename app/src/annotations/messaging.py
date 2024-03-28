from src.annotations.schemas import HypothesisAnnotationCreateOutput
from src.chat.schemas import MessageDB


def create_message_for_users(
    annotations: list[HypothesisAnnotationCreateOutput],
    message: MessageDB,
) -> str:
    if not annotations:
        return "No annotations created"

    len_of_annotations = len(annotations)
    # we are assuming that all annotations have the same data
    data_uri = annotations[0].uri
    prompt = ""
    if message.content_dict:
        prompt = message.content_dict.get("prompt", "")
    result = (
        f"Created **{len_of_annotations} annotations** "
        f"from [{data_uri}]({data_uri}), with the prompt: {prompt}"
    )
    return result


def create_message_for_ai_history(
    annotations: list[HypothesisAnnotationCreateOutput],
) -> str:
    data = "\n".join(
        [
            f"{anno_data.target[0].selector[0].model_dump(mode='json')}"
            for anno_data in annotations
        ]
    )
    return f"ANNOTATED DATA: {data}"
