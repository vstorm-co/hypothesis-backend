AVAILABLE_MODELS = {
    "OpenAI": [
        "gpt-4-1106-preview",
        "gpt-3.5-turbo-1106",
        "gpt-4-turbo-2024-04-09",
        "gpt-4o-2024-05-13",
        "o1-preview",
    ],
    "Claude": [
        "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229",
    ],
    "Groq": [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.1-405b",
        "mixtral-8x7b-32768",
    ],
}

MAX_INPUT_SIZE_MAP = {
    "llama-3.1-70b-versatile": 30_000,
    "llama-3.1-8b-instant": 30_000,
    "llama-3.1-405b": 127_000,
    "mixtral-8x7b-32768": 30_000,
    "gpt-4o-2024-05-13": 127_000,
    "gpt-4-turbo-2024-04-09": 127_000,
    "gpt-4-1106-preview": 127_000,
    "o1-preview": 127_000,
    "claude-3-haiku-20240307": 127_000,
    "claude-3-sonnet-20240229": 127_000,
    "claude-3-opus-20240229": 127_000,
}
