from logging import getLogger

import tiktoken
from tiktoken import Encoding

from src.chat.constants import MODEL_NAME

logger = getLogger(__name__)


def num_tokens_from_string(string: str, encoding: Encoding) -> int:
    """Returns the number of tokens in a text string."""
    num_tokens = len(encoding.encode(string))
    return num_tokens


def count_content_tokens(
    content: str, model=MODEL_NAME, add_calculates: bool = False
) -> int:
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4-1106-preview",
        "gpt-4-turbo-2024-04-09",
    }:
        tokens_per_message = 3
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = (
            4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        )
    elif "gpt-3.5-turbo" in model:
        logger.warning(
            """Warning: gpt-3.5-turbo may update over time.
            Returning num tokens assuming gpt-3.5-turbo-0613."""
        )
        return count_content_tokens(content, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model or model.startswith("gpt-4"):
        logger.warning(
            """Warning: gpt-4 may update over time.
            Returning num tokens assuming gpt-4-0613."""
        )
        return count_content_tokens(content, model="gpt-4-1106-preview")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}.
            See https://github.com/openai/openai-python/blob/main/chatml.md for
            information on how messages are converted to tokens."""
        )

    num_tokens = 0
    num_tokens += num_tokens_from_string(content, encoding=encoding)
    if add_calculates:
        num_tokens += tokens_per_message
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens
