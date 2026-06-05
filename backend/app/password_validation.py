"""
Shared password strength validation for registration and password updates.
"""
from __future__ import annotations

import re

MIN_PASSWORD_LENGTH = 8
SPECIAL_CHAR_PATTERN = re.compile(r'[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;/\'`~]')

COMMON_PASSWORDS = frozenset(
    {
        "123456",
        "1234567",
        "12345678",
        "123456789",
        "1234567890",
        "12345",
        "1234",
        "123123",
        "111111",
        "000000",
        "password",
        "password1",
        "password123",
        "passw0rd",
        "qwerty",
        "qwerty123",
        "qwertyuiop",
        "abc123",
        "admin",
        "admin123",
        "letmein",
        "welcome",
        "welcome1",
        "monkey",
        "dragon",
        "master",
        "login",
        "shadow",
        "sunshine",
        "princess",
        "football",
        "baseball",
        "iloveyou",
        "trustno1",
        "superman",
        "batman",
        "access",
        "hello",
        "charlie",
        "donald",
        "mustang",
        "696969",
        "654321",
        "987654321",
        "qazwsx",
        "asdfgh",
        "zxcvbnm",
        "1q2w3e4r",
        "1qaz2wsx",
        "aa123456",
        "p@ssw0rd",
        "changeme",
        "secret",
        "test123",
        "guest",
        "root",
        "toor",
    }
)


def validate_password(password: str) -> None:
    """
    Validate password strength. Raises ValueError with a user-friendly message
    when the password does not meet requirements.
    """
    errors: list[str] = []

    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")

    if not SPECIAL_CHAR_PATTERN.search(password):
        errors.append("Password must contain at least one special character")

    normalized = password.strip().lower()
    if normalized in COMMON_PASSWORDS or password in COMMON_PASSWORDS:
        errors.append("This password is too common. Please choose a stronger one")

    if errors:
        raise ValueError("; ".join(errors))
