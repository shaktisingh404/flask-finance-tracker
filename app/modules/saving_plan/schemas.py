from marshmallow import EXCLUDE
from app.core.schemas import BaseSchema
from app.core.constants import SavingPlanStatus, Frequency
from datetime import date
from marshmallow import fields, validates, ValidationError, validates_schema, pre_load
from app.core.validators import validate_amount, validate_name
from .models import SavingPlan
from .tasks import send_savings_plan_completion_notification
from app.core.constants import SavingPlanStatus, Frequency


class BaseSavingPlanSchema(BaseSchema):
    """Base schema for saving plan with common fields and validations"""

    class Meta(BaseSchema.Meta):
        model = SavingPlan

    # name = fields.String(validate=validate_name,)
    name = fields.String(validate=validate_name)
    amount = fields.Decimal(validate=validate_amount, as_string=True)
    status = fields.Enum(SavingPlanStatus, by_value=True)
    frequency = fields.Enum(Frequency, by_value=True)

    @pre_load
    def strip_whitespace(self, data, **kwargs):
        """Strip whitespace from string fields before processing"""
        if data.get("name"):
            data["name"] = data["name"].strip()
        return data

    @validates("current_deadline")
    def validate_current_deadline(self, current_deadline):
        today = date.today()
        if current_deadline < today:
            raise ValidationError("Deadline must be in the future")


class SavingPlanSchema(BaseSavingPlanSchema):
    """Schema for creating and retrieving saving plans"""

    class Meta(BaseSavingPlanSchema.Meta):
        model = SavingPlan
        fields = (
            "id",
            "name",
            "amount",
            "original_deadline",
            "current_deadline",
            "status",
            "frequency",
            "created_at",
            "updated_at",
            "user_id",
            "progress_percentage",
            "saved_amount",
            "remaining_amount",
            "time_remaining",
            "required_contribution",
            "is_deleted",
        )
        dump_only = (
            "id",
            "created_at",
            "updated_at",
            "is_deleted",
            "original_deadline",
            "progress_percentage",
            "saved_amount",
            "remaining_amount",
            "time_remaining",
            "required_contribution",
        )

    user_id = fields.UUID(required=True)
    saved_amount = fields.Decimal(as_string=True)
    progress_percentage = fields.Method("calculate_progress")
    remaining_amount = fields.Method("calculate_remaining")
    time_remaining = fields.Method("calculate_time_remaining")
    required_contribution = fields.Method("calculate_required_contribution")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calculator = SavingPlanCalculator()

    def calculate_required_contribution(self, obj):
        return self.calculator.calculate_required_contribution(obj)

    def calculate_progress(self, obj):
        return self.calculator.calculate_progress(obj)

    def calculate_remaining(self, obj):
        return self.calculator.calculate_remaining(obj)

    def calculate_time_remaining(self, obj):
        return self.calculator.calculate_time_remaining(obj)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        data["original_deadline"] = data["current_deadline"]
        return data


class SavingPlanUpdateSchema(BaseSavingPlanSchema):
    """Schema for updating saving plans"""

    class Meta(BaseSavingPlanSchema.Meta):
        fields = [
            "name",
            "amount",
            "current_deadline",
            "status",
            "frequency",
            "updated_at",
        ]
        dump_only = ["updated_at"]

    @validates("current_deadline")
    def validate_update_deadline(self, deadline):
        super().validate_current_deadline(deadline)
        instance = self.context.get("instance")

        if instance:
            if instance.status == SavingPlanStatus.COMPLETED:
                raise ValidationError("Cannot modify deadline of completed saving plan")
            if deadline < instance.original_deadline:
                raise ValidationError(
                    "New deadline cannot be earlier than the original deadline"
                )

        return deadline

    @validates_schema
    def validate_update_schema(self, data, **kwargs):
        instance = self.context.get("instance")

        calculator = SavingPlanCalculator()
        progress = calculator.calculate_progress_value(
            instance, data.get("amount", instance.amount)
        )

        if progress >= 100 and instance.status != SavingPlanStatus.COMPLETED:
            send_savings_plan_completion_notification.delay(instance.id)
            data["status"] = SavingPlanStatus.COMPLETED
        elif progress < 100 and instance.status == SavingPlanStatus.COMPLETED:
            data["status"] = SavingPlanStatus.ACTIVE
        return data


class SavingPlanCalculator:
    """Handle all saving plan calculations"""

    def calculate_progress_value(self, obj, target_amount):
        """Calculate raw progress percentage"""
        amount_saved = float(obj.saved_amount or 0)
        target = float(target_amount)
        return (amount_saved / target * 100) if target > 0 else 0

    def calculate_progress(self, obj):
        """Format progress percentage"""
        progress = self.calculate_progress_value(obj, obj.amount)
        return f"{progress:.2f}"

    def calculate_remaining(self, obj):
        """Calculate and format remaining amount"""
        amount_saved = float(obj.saved_amount or 0)
        remaining = max(float(obj.amount) - amount_saved, 0)
        return f"{remaining:.2f}"

    def calculate_time_remaining(self, obj):
        """Calculate and format time remaining"""
        if not obj.current_deadline:
            return "Unknown"

        days_remaining = (obj.current_deadline - date.today()).days

        if days_remaining <= 0:
            return "0 days"
        elif days_remaining < 30:
            return f"{days_remaining} days"
        elif days_remaining < 365:
            months = days_remaining // 30
            return f"{months} {'month' if months == 1 else 'months'}"

        years = days_remaining // 365
        months = (days_remaining % 365) // 30

        if months > 0:
            return f"{years} {'year' if years == 1 else 'years'}, {months} {'month' if months == 1 else 'months'}"
        return f"{years} {'year' if years == 1 else 'years'}"

    def calculate_required_contribution(self, obj):
        """Calculate required periodic contribution to meet the goal"""
        if not obj.current_deadline:
            return "0.00"

        remaining_amount = float(self.calculate_remaining(obj))
        days_remaining = (obj.current_deadline - date.today()).days

        if days_remaining <= 0:
            return "0.00"

        if obj.frequency == Frequency.MONTHLY:
            remaining_periods = max((days_remaining + 29) // 30, 1)
        elif obj.frequency == Frequency.WEEKLY:
            remaining_periods = max((days_remaining + 6) // 7, 1)
        else:  # YEARLY
            remaining_periods = max((days_remaining + 364) // 365, 1)

        required_per_period = remaining_amount / remaining_periods
        return f"{required_per_period:.2f}"
