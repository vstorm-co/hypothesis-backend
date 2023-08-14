import contextlib
import logging
import random
import string
from src.config import get_settings

logger = logging.getLogger(__name__)
ALPHA_NUM = string.ascii_letters + string.digits


def generate_random_alphanum(length: int = 20) -> str:
    return "".join(random.choices(ALPHA_NUM, k=length))


@contextlib.contextmanager
def override_settings(**overrides):
    settings = get_settings()
    original = {}

    try:
        for key, value in overrides.items():
            original[key] = getattr(settings, key)
            setattr(settings, key, value)

        yield
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
