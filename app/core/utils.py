import re


from flask import request, g
from flask_restful import Resource
from app.core.logger import logger
from app.core.pagination import paginate


def is_valid_email(email):
    """Check if an email is valid."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_strong_password(password):
    """
    Check if a password is strong.
    Requirements:
    - At least 8 characters
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True


class BaseListResource(Resource):
    """
    Base resource class for listing items with common filtering and pagination.
    Subclasses must define:
    - model: The SQLAlchemy model class
    - schema: The marshmallow schema for serialization
    - endpoint: The API endpoint name
    - type_enum: Optional enum class for type filtering (if applicable)
    """

    model = None
    schema = None
    endpoint = None
    type_enum = None

    def get_queryset(self, **kwargs):
        """Base queryset - override in subclass if needed."""
        if not self.model:
            raise ValueError("Model must be defined in subclass")
        return self.model.query.filter(
            getattr(self.model, "is_deleted", False) == False
        ).order_by(self.model.created_at.desc())

    def apply_type_filter(self, queryset):
        """Apply type filter if type_enum is defined and type param is provided."""
        if not self.type_enum:
            return queryset

        type_value = request.args.get("type")
        if type_value and type_value in self.type_enum.__members__:
            return queryset.filter(self.model.type == type_value)
        return queryset

    def get(self, **kwargs):
        """Handle GET request with pagination and filtering."""
        if not all([self.model, self.schema, self.endpoint]):
            raise ValueError("Model, schema, and endpoint must be defined in subclass")

        logger.info(
            f"Fetching {self.model.__name__.lower()}s for user: {g.current_user.id}"
        )

        # Get base queryset (can be modified by subclass)
        queryset = self.get_queryset(**kwargs)

        # Apply type filter if applicable
        queryset = self.apply_type_filter(queryset)

        # Paginate results
        result = paginate(
            query=queryset,
            schema=self.schema,
            endpoint=self.endpoint,
        )

        logger.info(
            f"{self.model.__name__.lower()}s retrieved successfully for user: {g.current_user.id}"
        )
        return result, 200
