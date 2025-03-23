from marshmallow import ValidationError
import re

from uuid import UUID

from app.core.utils import is_valid_email, is_strong_password
from app.modules.category.models import Category
from app.extensions import db
from app.core.constants import (
    MIN_NAME_LENGTH,
    MAX_NAME_LENGTH,
    MIN_USERNAME_LENGTH,
    MAX_USERNAME_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_AMOUNT,
    MAX_AMOUNT,
)


def validate_username(username):
    """Validate username format."""

    if len(username) < MIN_USERNAME_LENGTH or len(username) > MAX_USERNAME_LENGTH:
        raise ValidationError(
            f"Username must be between {MIN_USERNAME_LENGTH} and {MAX_USERNAME_LENGTH} characters."
        )

    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise ValidationError(
            "Username can only contain letters, numbers, and underscores."
        )


def validate_email(email):
    """Validate email format."""

    if not is_valid_email(email):
        raise ValidationError("Invalid email format.")


def validate_name(name):
    """Validate name format."""

    if len(name) < MIN_NAME_LENGTH or len(name) > MAX_NAME_LENGTH:
        raise ValidationError(
            f"Name must be between {MIN_NAME_LENGTH} and {MAX_NAME_LENGTH} characters."
        )

    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        raise ValidationError(
            "Name can only contain letters, spaces, hyphens, and apostrophes."
        )


def validate_password(password):
    """Validate password strength."""
    if not password:
        raise ValidationError("Password cannot be empty.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )

    if not is_strong_password(password):
        raise ValidationError(
            "Password must contain at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character."
        )


def validate_date_of_birth(date_of_birth):
    """Validate date of birth."""
    if not date_of_birth:
        raise ValidationError("Date of birth cannot be empty.")

    if date_of_birth.year < 1900:
        raise ValidationError("Date of birth must be after 1900.")

    if date_of_birth.year > 2021:
        raise ValidationError("Date of birth must be before 2021.")


def validate_amount(amount):
    """Validate transaction amount."""
    if amount <= MIN_AMOUNT or amount > MAX_AMOUNT:
        raise ValidationError(f"Amount must be between {MIN_AMOUNT} and {MAX_AMOUNT}.")


def validate_category_name(value):
    """Validate that category name is unique for the user."""

    value = value.strip().capitalize()

    if len(value) < MIN_NAME_LENGTH or len(value) > MAX_NAME_LENGTH:
        raise ValidationError(
            f"Name must be between {MIN_NAME_LENGTH} and {MAX_NAME_LENGTH} characters."
        )

    if not re.match(r"^[a-zA-Z0-9\s\-']+$", value):
        raise ValidationError(
            "Name can only contain letters, numbers, spaces, hyphens, and apostrophes."
        )
    return value


def is_valid_uuid(value):
    """Check if a value is a valid UUID"""
    if not value:
        return False

    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False
