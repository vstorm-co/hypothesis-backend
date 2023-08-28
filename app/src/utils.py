import contextlib
import logging
import os
import random
import string
from pathlib import Path

from src.config import get_settings

logger = logging.getLogger(__name__)
ALPHA_NUM = string.ascii_letters + string.digits


def get_root_path() -> Path:
    """return root path of project"""
    return Path(os.path.dirname(os.path.abspath(__file__)))


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
