from marshmallow import fields, validates, validates_schema, ValidationError, EXCLUDE
from marshmallow.validate import Range
from app.extensions import ma
from app.modules.budget.models import Budget
from app.modules.category.models import Category
from app.modules.user.models import User
from app.core.constants import UserRole, MIN_AMOUNT, MAX_AMOUNT
from flask import g
from decimal import Decimal
import datetime
from app.core.schemas import BaseSchema
from app.core.validators import validate_amount
from app.modules.category.schemas import CategorySchema


class BudgetSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Budget
        include_fk = True
        fields = (
            "id",
            "user_id",
            "category_id",
            "category",
            "amount",
            "spent_amount",
            "month",
            "year",
            "is_deleted",
            "created_at",
            "updated_at",
        )
        dump_only = (
            "id",
            "spent_amount",
            "is_deleted",
            "created_at",
            "updated_at",
        )
        load_only = "category_id"

    amount = fields.Decimal(
        required=True, places=2, as_string=True, validate=validate_amount
    )
    spent_amount = fields.Decimal(places=2, as_string=True, dump_only=True)
    category = fields.Nested(
        CategorySchema, only=("id", "name", "is_predefined"), dump_only=True
    )

    @validates("category_id")
    def validate_category_id(self, value):
        """Validate category exists and is not deleted"""
        validate_category(value)
        return value

    @validates_schema
    def validate_category_ownership(self, data, **kwargs):
        """Validate category belongs to user"""
        category_id = data.get("category_id")
        user_id = data.get("user_id")
        validate_category(category_id, user_id)

    @validates("month")
    def validate_month(self, value):
        """Validate month is between 1 and 12"""
        if not 1 <= value <= 12:
            raise ValidationError("Month must be between 1 and 12", "month")
        return value

    @validates("year")
    def validate_year(self, value):
        """Validate year is not in the past"""
        current_year = datetime.datetime.now().year
        if value < current_year:
            raise ValidationError("Year cannot be in the past", "year")
        return

    @validates_schema
    def validate_unique_budget(self, data, **kwargs):
        """Validate uniqueness: one budget per user-category-month-year"""
        check_existing_budget(
            data["user_id"], data["category_id"], data["month"], data["year"]
        )


class BudgetUpdateSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Budget
        include_fk = True
        fields = ("amount",)

    amount = fields.Decimal(
        required=True, places=2, as_string=True, validate=validate_amount
    )


def validate_category(category_id, user_id=None):
    """
    Validate category exists, is not deleted, and optionally belongs to user

    Args:
        category_id: ID of the category to validate
        user_id: Optional user ID to check ownership

    Raises:
        ValidationError: If validation fails
    """
    category = Category.query.get(category_id)
    if not category or category.is_deleted:
        raise ValidationError("Category not found", "category_id")

    if user_id and category.user_id != user_id:
        raise ValidationError("Category does not belong to this user", "category_id")

    return category


def check_existing_budget(user_id, category_id, month, year):
    """
    Check if a budget already exists for given parameters

    Raises:
        ValidationError: If budget already exists
    """
    existing = Budget.query.filter(
        Budget.user_id == user_id,
        Budget.category_id == category_id,
        Budget.month == month,
        Budget.year == year,
        Budget.is_deleted == False,
    ).first()

    if existing:
        raise ValidationError(
            "A budget already exists for this user, category, month and year",
            "month_year",
        )
