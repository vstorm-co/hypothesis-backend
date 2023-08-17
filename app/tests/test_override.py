import pytest

import src.utils
from src.config import get_settings


def test_override_settings(override_settings):
    settings = get_settings()
    assert settings.DEBUG is True

    with override_settings(DEBUG=False):
        assert settings.DEBUG is False

    assert settings.DEBUG is True

    # Make sure first valid params are reverted to their original values
    with pytest.raises(
        AttributeError, match="'Config' object has no attribute 'not_existant'"
    ):
        with override_settings(DEBUG=False, not_existant=True):
            pass

    assert settings.DEBUG is True


@src.utils.override_settings(DEBUG=False)
def test_override_settings_decorator():
    settings = get_settings()

    assert settings.DEBUG is False


def test_settings():
    settings = get_settings()

    assert settings.DEBUG is True
