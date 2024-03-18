from src.annotations.schemas import HypothesisAnnotationCreateOutput


def create_message_for_users(
    annotations: list[HypothesisAnnotationCreateOutput],
) -> str:
    if not annotations:
        return "No annotations created"

    len_of_annotations = len(annotations)
    data = annotations[0]  # we are assuming that all annotations have the same data

    result = (
        f"Created **{len_of_annotations} annotations** "
        f"from [{data.uri}]({data.uri}), with the prompt: {data.text}"
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
