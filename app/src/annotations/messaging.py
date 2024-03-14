from src.annotations.schemas import HypothesisAnnotationCreateOutput


def create_message_for_users(data: HypothesisAnnotationCreateOutput) -> str:
    result = (
        f"Created **{len(data.target[0].selector)} annotations** "
        f"from [{data.uri}]({data.uri}), with the prompt: {data.text}"
    )
    return result


def create_message_for_ai_history(data: HypothesisAnnotationCreateOutput) -> str:
    return f"ANNOTATED DATA: {data.target[0].selector}"
