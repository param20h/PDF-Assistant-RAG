import pytest

from app.password_validation import validate_password


def test_validate_password_accepts_strong_password():
    validate_password("Password1!")


def test_validate_password_rejects_common_password():
    with pytest.raises(ValueError, match="too common"):
        validate_password("password123")


def test_validate_password_rejects_short_password():
    with pytest.raises(ValueError, match="8 characters"):
        validate_password("Pass1!")


def test_validate_password_rejects_missing_character_classes():
    with pytest.raises(ValueError, match="uppercase"):
        validate_password("password1!")

    with pytest.raises(ValueError, match="lowercase"):
        validate_password("PASSWORD1!")

    with pytest.raises(ValueError, match="number"):
        validate_password("Password!")

    with pytest.raises(ValueError, match="special character"):
        validate_password("Password1")
