from datetime import datetime
from marshmallow import fields, validates, validates_schema, ValidationError
from app.core.validators import validate_amount
from app.core.constants import Frequency, TransactionType
from app.core.schemas import BaseSchema
from app.modules.user.models import User
from app.modules.category.models import Category
from app.modules.saving_plan.models import SavingPlan
from .models import RecurringTransaction
from flask import g
from app.modules.category.schemas import CategorySchema
from app.modules.saving_plan.schemas import SavingPlanSchema


class BaseRecurringTransactionSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = RecurringTransaction

    user_id = fields.UUID(required=True)
    category_id = fields.UUID(required=False, allow_none=True)
    saving_plan_id = fields.UUID(required=False, allow_none=True)
    type = fields.Enum(TransactionType, by_value=True, required=True)
    amount = fields.Decimal(required=True, validate=validate_amount, as_string=True)
    frequency = fields.Enum(Frequency, by_value=True, required=True)
    starts_at = fields.DateTime(required=True)
    ends_at = fields.DateTime(allow_none=True)
    category = fields.Nested(
        CategorySchema, only=("id", "name", "is_predefined"), dump_only=True
    )
    saving_plan = fields.Nested(SavingPlanSchema, only=("id", "name"), dump_only=True)

    def _get_user(self, user_id):
        """Helper method to get user by ID."""
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            raise ValidationError("User not found")
        return user

    def _get_category(self, category_id, user_id):
        """Helper method to get category by ID."""
        category = Category.query.filter(
            Category.id == category_id,
            Category.is_deleted == False,
        ).first()

        if not category:
            raise ValidationError("Category not found")
        if not category.is_predefined and category.user_id != user_id:
            raise ValidationError("Category does not belong to the user")

        return category

    def _get_saving_plan(self, saving_plan_id, user_id):
        """Helper method to get and validate saving plan."""
        saving_plan = SavingPlan.query.filter_by(
            id=saving_plan_id, user_id=user_id, is_deleted=False
        ).first()

        if not saving_plan:
            raise ValidationError("Saving plan not found")

        if saving_plan.status in ["COMPLETED", "PAUSED"]:
            raise ValidationError(
                f"Cannot add transactions to a {saving_plan.status.lower()} savings plan"
            )
        return saving_plan

    @validates("starts_at")
    def validate_starts_at(self, value):
        """Validate start date is not in the past."""
        if value < datetime.now():
            raise ValidationError("Start date and time cannot be in the past")
        return value

    @validates("type")
    def validate_type(self, value):
        """Validate transaction type with savings plan."""
        if (
            self.context.get("data", {}).get("saving_plan_id")
            and value != TransactionType.DEBIT
        ):
            raise ValidationError("Savings plan transactions must be of type DEBIT")
        return value

    @validates_schema
    def validate_schema(self, data, **kwargs):
        """Cross-field validations."""
        user = self._get_user(data["user_id"])
        category_id = data.get("category_id")
        saving_plan_id = data.get("saving_plan_id")

        # Validate category or saving plan existence
        if category_id and saving_plan_id:
            raise ValidationError(
                "Transaction can only be associated with either category or saving plan"
            )
        if not category_id and not saving_plan_id:
            raise ValidationError(
                "Transaction must be associated with either category or saving plan"
            )

        # Validate references
        if category_id:
            self._get_category(category_id, user.id)
        if saving_plan_id:
            self._get_saving_plan(saving_plan_id, user.id)

        # Validate dates
        if data.get("ends_at"):
            if data["ends_at"].date() <= data["starts_at"].date():
                raise ValidationError("End date must be after start date")


class RecurringTransactionSchema(BaseRecurringTransactionSchema):
    """Schema for creating and retrieving recurring transactions."""

    class Meta(BaseRecurringTransactionSchema.Meta):
        fields = (
            "id",
            "amount",
            "description",
            "type",
            "ends_at",
            "starts_at",
            "next_transaction_at",
            "category_id",
            "category",
            "saving_plan",
            "saving_plan_id",
            "user_id",
            "is_deleted",
            "created_at",
            "updated_at",
            "frequency",
        )
        dump_only = (
            "id",
            "is_deleted",
            "created_at",
            "updated_at",
            "next_transaction_at",
        )
        load_only = ("category_id", "saving_plan_id")


class RecurringTransactionUpdateSchema(BaseRecurringTransactionSchema):
    """Schema for updating recurring transactions."""

    @validates_schema
    def validate_update_schema(self, data, **kwargs):
        """Update-specific validations."""
        self._process_uuid_fields(data)
        super().validate_schema(data, **kwargs)

    def _process_uuid_fields(self, data):
        """Convert empty strings to None for UUID fields."""
        uuid_fields = ["category_id", "saving_plan_id"]
        for field in uuid_fields:
            if field in data and not data[field]:
                data[field] = None
