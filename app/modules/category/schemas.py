from marshmallow import (
    ValidationError,
    validates,
    fields,
    validates_schema,
    EXCLUDE,
)
from app.core.constants import UserRole
from flask import g
from app import ma, db
from app.modules.category.models import Category
from app.modules.user.models import User
from app.core.validators import validate_category_name
from app.core.schemas import BaseSchema


class CategorySchema(BaseSchema):
    """Schema for Category model with validation."""

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "user_id",
            "is_predefined",
            "created_at",
            "updated_at",
            "is_deleted",
        ]
        dump_only = (
            "id",
            "created_at",
            "updated_at",
            "is_deleted",
            "is_predefined",
        )
        unknown = EXCLUDE

    # Field definitions with validation
    name = fields.String(required=True, validate=validate_category_name)
    user_id = fields.UUID(required=True)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        """Additional schema-level validation."""
        if "name" in data and "user_id" in data:
            # Normalize the name
            normalized_name = validate_category_name(data["name"])

            # Check uniqueness
            is_unique, error_message = check_category_name_uniqueness(
                normalized_name, data["user_id"]
            )

            if not is_unique:
                raise ValidationError({"name": error_message})

            # Update with normalized value
            data["name"] = normalized_name
        return data


class CategoryUpdateSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Category

    @validates_schema
    def validate_schema(self, data, **kwargs):
        instance = getattr(self, "instance", None)

        if "name" in data and instance:
            normalized_name = validate_category_name(data["name"])

            category_id = instance.id
            user_id = instance.user_id

            is_unique, error_message = check_category_name_uniqueness(
                normalized_name,
                user_id,
                category_id,
            )

            if not is_unique:
                raise ValidationError({"name": error_message})

            # Update with normalized value
            data["name"] = normalized_name

        return data


def check_category_name_uniqueness(normalized_name, user_id, category_id=None):
    """
    Check if a category name is unique for a given user or as a predefined category.

    Args:
        normalized_name: The normalized category name to check
        user_id: The user ID to check against
        category_id: Optional - ID of current category (to exclude from uniqueness check during updates)

    Returns:
        A tuple (is_unique, error_message) where is_unique is a boolean and error_message is None or the validation error
    """
    # Check if this name already exists for this user
    query = db.session.query(Category).filter(
        Category.name == normalized_name,
        Category.user_id == user_id,
        Category.is_deleted == False,
    )

    # If we're updating an existing category, exclude it from the check
    if category_id:
        query = query.filter(Category.id != category_id)

    existing_user_category = query.first()

    # Check if a predefined category with this name exists
    predefined_query = db.session.query(Category).filter(
        Category.name == normalized_name, Category.is_predefined == True
    )

    # If we're updating a predefined category, exclude it
    if category_id:
        predefined_query = predefined_query.filter(Category.id != category_id)

    existing_predefined = predefined_query.first()

    # If either exists, return error
    if existing_user_category:
        return False, f"Category name '{normalized_name}' already exists for this user"

    if existing_predefined:
        return (
            False,
            f"Category name '{normalized_name}' already exists as a predefined category",
        )

    return True, None
