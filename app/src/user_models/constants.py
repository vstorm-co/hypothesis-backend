from logging import getLogger
from typing import Dict, List, Tuple

import openai
from anthropic import Anthropic
from groq import Groq

logger = getLogger(__name__)

# Context windows for various models
KNOWN_CONTEXT_WINDOWS = {
    "llama-3.1-70b-versatile": 30_000,
    "llama-3.1-405b": 127_000,
    # openai
    "babbage-002": 30000,
    "chatgpt-4o-latest": 30000,
    "dall-e-2": 30000,
    "dall-e-3": 30000,
    "davinci-002": 30000,
    "gpt-3.5-turbo": 30000,
    "gpt-3.5-turbo-0125": 30000,
    "gpt-3.5-turbo-1106": 30000,
    "gpt-3.5-turbo-16k": 30000,
    "gpt-3.5-turbo-instruct": 30000,
    "gpt-3.5-turbo-instruct-0914": 30000,
    "gpt-4": 127000,
    "gpt-4-0125-preview": 127000,
    "gpt-4-0613": 127000,
    "gpt-4-1106-preview": 127000,
    "gpt-4-turbo": 127000,
    "gpt-4-turbo-2024-04-09": 127000,
    "gpt-4-turbo-preview": 127000,
    "gpt-4o": 127000,
    "gpt-4o-2024-05-13": 127000,
    "gpt-4o-2024-08-06": 127000,
    "gpt-4o-2024-11-20": 127000,
    "gpt-4o-audio-preview": 127000,
    "gpt-4o-audio-preview-2024-10-01": 127000,
    "gpt-4o-audio-preview-2024-12-17": 127000,
    "gpt-4o-mini": 127000,
    "gpt-4o-mini-2024-07-18": 127000,
    "gpt-4o-mini-audio-preview": 127000,
    "gpt-4o-mini-audio-preview-2024-12-17": 127000,
    "gpt-4o-mini-realtime-preview": 127000,
    "gpt-4o-mini-realtime-preview-2024-12-17": 127000,
    "gpt-4o-realtime-preview": 127000,
    "gpt-4o-realtime-preview-2024-10-01": 127000,
    "gpt-4o-realtime-preview-2024-12-17": 127000,
    "o1": 30000,
    "o1-2024-12-17": 30000,
    "o1-mini": 30000,
    "o1-mini-2024-09-12": 30000,
    "o1-preview": 127000,
    "o1-preview-2024-09-12": 30000,
    "omni-moderation-2024-09-26": 30000,
    "omni-moderation-latest": 30000,
    "text-embedding-3-large": 30000,
    "text-embedding-3-small": 30000,
    "text-embedding-ada-002": 30000,
    "tts-1": 30000,
    "tts-1-1106": 30000,
    "tts-1-hd": 30000,
    "tts-1-hd-1106": 30000,
    "whisper-1": 30000,
    # claude
    "claude-2.0": 30000,
    "claude-2.1": 30000,
    "claude-3-5-haiku-20241022": 127000,
    "claude-3-5-sonnet-20240620": 127000,
    "claude-3-5-sonnet-20241022": 127000,
    "claude-3-haiku-20240307": 127000,
    "claude-3-opus-20240229": 127000,
    "claude-3-sonnet-20240229": 127000,
    # groq
    "deepseek-r1-distill-llama-70b": 127000,
    "distil-whisper-large-v3-en": 30000,
    "gemma2-9b-it": 30000,
    "llama-3.1-8b-instant": 30000,
    "llama-3.2-11b-vision-preview": 127000,
    "llama-3.2-1b-preview": 127000,
    "llama-3.2-3b-preview": 127000,
    "llama-3.2-90b-vision-preview": 127000,
    "llama-3.3-70b-specdec": 127000,
    "llama-3.3-70b-versatile": 127000,
    "llama-guard-3-8b": 30000,
    "llama3-70b-8192": 30000,
    "llama3-8b-8192": 30000,
    "mixtral-8x7b-32768": 30000,
    "whisper-large-v3": 30000,
    "whisper-large-v3-turbo": 30000,
}


def get_openai_models(api_key: str | None = None) -> Tuple[List[str], Dict[str, int]]:
    if not api_key:
        raise ValueError("OpenAI API key not configured")

    client = openai.OpenAI(api_key=api_key)
    models = client.models.list()
    model_list = []
    context_windows = {}

    for model in models:
        model_list.append(model.id)
        context_windows[model.id] = KNOWN_CONTEXT_WINDOWS.get(
            model.id, 127_000 if str(model.id).startswith("gpt-4") else 30_000
        )

    return model_list, context_windows


def get_anthropic_models(
    api_key: str | None = None,
) -> Tuple[List[str], Dict[str, int]]:
    if not api_key:
        raise ValueError("Anthropic API key not configured")

    client = Anthropic(api_key=api_key)
    models = client.models.list()
    model_list = []
    context_windows = {}

    for model in models:
        model_list.append(model.id)
        context_windows[model.id] = KNOWN_CONTEXT_WINDOWS.get(
            model.id, 127_000 if str(model.id).startswith("claude-3") else 30_000
        )

    return model_list, context_windows


def get_groq_models(api_key: str | None = None) -> Tuple[List[str], Dict[str, int]]:
    if not api_key:
        raise ValueError("Groq API key not configured")

    client = Groq(api_key=api_key)
    models = client.models.list()
    model_list = []
    context_windows = {}

    for model in models.data:
        model_list.append(model.id)
        context_windows[model.id] = KNOWN_CONTEXT_WINDOWS.get(
            model.id,
            127_000
            if (
                str(model.id).startswith("deepseek")
                or str(model.id).startswith("llama-3")
            )
            else 30_000,
        )

    return model_list, context_windows


async def get_available_models(
    api_key: str | None = None, provider: str | None = None
) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    all_context_windows = {}
    available_models = {}

    if provider:
        provider = provider.lower()
        try:
            if provider == "openai":
                models, windows = get_openai_models(api_key)
                available_models["openai"] = models
                all_context_windows.update(windows)
            elif provider == "claude":
                models, windows = get_anthropic_models(api_key)
                available_models["claude"] = models
                all_context_windows.update(windows)
            elif provider == "groq":
                models, windows = get_groq_models(api_key)
                available_models["groq"] = models
                all_context_windows.update(windows)
        except Exception as e:
            logger.error(f"Error fetching models for {provider}: {e}")
            available_models[provider.capitalize()] = []
    else:
        # Default behavior without API key for initial loading
        available_models = {
            "openai": list(k for k in KNOWN_CONTEXT_WINDOWS if k.startswith("gpt")),
            "claude": list(k for k in KNOWN_CONTEXT_WINDOWS if k.startswith("claude")),
            "groq": list(
                k for k in KNOWN_CONTEXT_WINDOWS if k.startswith(("llama", "mixtral"))
            ),
        }
        all_context_windows = KNOWN_CONTEXT_WINDOWS

    return available_models, all_context_windows


# Models that don't support streaming responses
NON_STREAMABLE_MODELS = [
    "o1-preview",
]
