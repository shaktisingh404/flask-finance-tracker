from datetime import datetime
from marshmallow import fields, validates, validates_schema, ValidationError, post_load
from app.core.validators import is_valid_uuid
from app.core.constants import UserRole
from app.core.schemas import BaseSchema
from app.modules.transaction.models import Transaction
from app.modules.user.models import User
from app.core.validators import validate_amount
from app.modules.category.models import Category
from app.core.constants import TransactionType
from app.modules.saving_plan.models import SavingPlan
from flask import g
from app.modules.category.schemas import CategorySchema
from app.modules.saving_plan.schemas import SavingPlanSchema


class TransactionValidator:
    """Centralized validation logic for transactions"""

    @staticmethod
    def get_user(user_id):
        return User.query.filter_by(id=user_id).first()

    @staticmethod
    def get_saving_plan(saving_plan_id, user_id):
        return SavingPlan.query.filter(
            SavingPlan.id == saving_plan_id,
            SavingPlan.is_deleted == False,
            SavingPlan.user_id == user_id,
        ).first()

    @staticmethod
    def get_category(category_id, user_id):
        user_category = Category.query.filter(
            Category.id == category_id,
            Category.is_deleted == False,
            Category.user_id == user_id,
        ).first()
        return (
            user_category
            or Category.query.filter(
                Category.id == category_id,
                Category.is_predefined == True,
                Category.is_deleted == False,
            ).first()
        )

    @staticmethod
    def validate_user_permissions(current_user, target_user):
        if current_user.role == UserRole.ADMIN and target_user.role == UserRole.ADMIN:
            raise ValidationError(
                {"user": "Admin cannot create transactions for another Admin"}
            )


class BaseTransactionSchema(BaseSchema):
    class Meta:
        model = Transaction

    # Fields definition
    user_id = fields.UUID(required=True)
    category_id = fields.UUID(required=False)
    saving_plan_id = fields.UUID(required=False)
    type = fields.Enum(TransactionType, by_value=True, required=True)
    amount = fields.Decimal(required=True, validate=validate_amount, as_string=True)
    transaction_at = fields.DateTime(required=True, format="%m-%d-%Y %H:%M:%S")
    category = fields.Nested(
        CategorySchema, only=("id", "name", "is_predefined"), dump_only=True
    )
    saving_plan = fields.Nested(SavingPlanSchema, only=("id", "name"), dump_only=True)

    @validates("category_id")
    def validate_category(self, value):
        if not value:
            return
        if not is_valid_uuid(value):
            raise ValidationError("Invalid UUID format")
        category = TransactionValidator.get_category(value, self.context.get("user_id"))
        if not category:
            raise ValidationError(f"Category with ID {value} does not exist")

    @validates("saving_plan_id")
    def validate_saving_plan(self, value):
        if not value:
            return
        if not is_valid_uuid(value):
            raise ValidationError("Invalid UUID format")
        saving_plan = TransactionValidator.get_saving_plan(
            value, self.context.get("user_id")
        )
        if not saving_plan:
            raise ValidationError(f"Saving plan with ID {value} does not exist")

    @validates("transaction_at")
    def validate_transaction_date(self, value):
        saving_plan_id = self.context.get("data", {}).get("saving_plan_id")
        if not saving_plan_id:
            return
        saving_plan = TransactionValidator.get_saving_plan(
            saving_plan_id, self.context.get("user_id")
        )
        if saving_plan:
            if value.date() > saving_plan.current_deadline:
                raise ValidationError("Date exceeds saving plan deadline")
            if value.date() < saving_plan.created_at.date():
                raise ValidationError("Date precedes saving plan creation")

    @validates_schema
    def validate_schema(self, data, **kwargs):
        validator = TransactionValidator
        current_user = g.current_user
        user_id = data.get("user_id", getattr(self.instance, "user_id", None))
        self.context["user_id"] = user_id
        self.context["data"] = data

        target_user = validator.get_user(user_id)
        validator.validate_user_permissions(current_user, target_user)

        self._process_uuid_fields(data)
        self._validate_business_rules(data)

    def _process_uuid_fields(self, data):
        for field in ["category_id", "saving_plan_id"]:
            if field in data and not data[field]:
                data[field] = None

        # def _validate_business_rules(self, data):
        #     has_category = bool(data.get("category_id"))
        #     has_saving_plan = bool(data.get("saving_plan_id"))

        #     if has_category and has_saving_plan:
        #         raise ValidationError(
        #             {"error": "Cannot have both category and saving plan"}
        #         )
        #     if not has_category and not has_saving_plan:
        #         raise ValidationError({"error": "Must have either category or saving plan"})

        #     if has_saving_plan and data["type"] == TransactionType.DEBIT:
        #         raise ValidationError(
        #             {"type": "Debit transactions cannot use saving plans"}
        #         )

    def _validate_business_rules(self, data):
        has_category = bool(data.get("category_id"))
        has_saving_plan = bool(data.get("saving_plan_id"))

        if has_category and has_saving_plan:
            raise ValidationError(
                {"error": "Cannot have both category and saving plan"}
            )
        if not has_category and not has_saving_plan:
            raise ValidationError({"error": "Must have either category or saving plan"})

        if has_saving_plan and data["type"] == TransactionType.DEBIT:
            raise ValidationError(
                {"type": "Debit transactions cannot use saving plans"}
            )


class TransactionSchema(BaseTransactionSchema):
    class Meta(BaseTransactionSchema.Meta):
        fields = (
            "id",
            "user_id",
            "type",
            "amount",
            "category_id",
            "category",
            "saving_plan_id",
            "saving_plan",
            "description",
            "transaction_at",
            "created_at",
            "updated_at",
            "is_deleted",
        )
        dump_only = ("id", "created_at", "updated_at", "is_deleted")
        load_only = ("category_id", "saving_plan_id")

    transaction_at = fields.DateTime(format="%Y-%m-%d %H:%M:%S")

    @post_load
    def make_transaction(self, data, **kwargs):
        """Convert validated data into a Transaction object."""
        if not self.instance:  # Creation case
            return Transaction(**data)
        return data


class TransactionUpdateSchema(BaseTransactionSchema):
    class Meta(BaseTransactionSchema.Meta):
        fields = (
            "type",
            "amount",
            "category_id",
            "saving_plan_id",
            "transaction_at",
            "description",
            "updated_at",
        )
        dump_only = ("updated_at",)

    @validates_schema
    def validate_update_schema(self, data, **kwargs):
        super().validate_schema(data, **kwargs)
        if self.instance:
            self._validate_update_constraints(data)

    def _validate_update_constraints(self, data):
        current = self.instance
        new_type = data.get("type")
        new_category = data.get("category_id")
        new_saving_plan = data.get("saving_plan_id")

        if "category_id" in data or "saving_plan_id" in data:
            if current.category_id and new_saving_plan:
                raise ValidationError(
                    {"saving_plan_id": "Cannot switch to saving plan"}
                )
            if current.saving_plan_id and new_category:
                raise ValidationError({"category_id": "Cannot switch to category"})

        if new_type == TransactionType.DEBIT and (
            new_saving_plan or current.saving_plan_id
        ):
            raise ValidationError({"type": "Cannot use DEBIT with saving plan"})


# from datetime import datetime
# from marshmallow import fields, validates, validates_schema, ValidationError, post_load
# from app.core.validators import is_valid_uuid
# from app.core.constants import UserRole
# from app.core.schemas import BaseSchema
# from app.modules.transaction.models import Transaction
# from app.modules.user.models import User
# from app.core.validators import validate_amount
# from app.modules.category.models import Category
# from app.core.constants import TransactionType
# from app.modules.saving_plan.models import SavingPlan
# from flask import g, request
# from uuid import UUID


# class TransactionValidator:
#     @staticmethod
#     def get_user(user_id):
#         return User.query.filter_by(id=user_id).first()

#     @staticmethod
#     def get_saving_plan(saving_plan_id, user_id):
#         # Ensure saving_plan_id is a string for SQLAlchemy
#         return SavingPlan.query.filter(
#             SavingPlan.id == UUID(saving_plan_id),
#             SavingPlan.is_deleted == False,
#             SavingPlan.user_id == user_id,
#         ).first()

#     @staticmethod
#     def get_category(category_id, user_id):
#         return (
#             Category.query.filter(
#                 Category.id == UUID(category_id),
#                 Category.is_deleted == False,
#                 Category.user_id == user_id,
#             ).first()
#             or Category.query.filter(
#                 Category.id == UUID(category_id),
#                 Category.is_predefined == True,
#                 Category.is_deleted == False,
#             ).first()
#         )

#     @staticmethod
#     def validate_user_permissions(current_user, target_user):
#         if current_user.role == UserRole.ADMIN and target_user.role == UserRole.ADMIN:
#             raise ValidationError(
#                 {"user": "Admin cannot create transactions for another Admin"}
#             )


# class BaseTransactionSchema(BaseSchema):
#     class Meta:
#         model = Transaction

#     user_id = fields.UUID(required=True)
#     category_id = fields.UUID(required=False, allow_none=True)
#     saving_plan_id = fields.UUID(required=False, allow_none=True)
#     type = fields.Enum(TransactionType, by_value=True, required=True)
#     amount = fields.Decimal(required=True, validate=validate_amount, as_string=True)
#     transaction_at = fields.DateTime(
#         required=True, default=datetime.utcnow, format="%Y-%m-%d %H:%M:%S"
#     )
#     description = fields.Str(required=False, allow_none=True)

#     @validates("category_id")
#     def validate_category(self, value):
#         if not value:
#             return
#         category = TransactionValidator.get_category(
#             UUID(value), self.context.get("user_id")
#         )
#         if not category:
#             raise ValidationError(f"Category with ID {value} does not exist")

#     @validates("saving_plan_id")
#     def validate_saving_plan(self, value):
#         if not value:
#             return
#         saving_plan = TransactionValidator.get_saving_plan(
#             UUID(value), self.context.get("user_id")
#         )
#         if not saving_plan:
#             raise ValidationError(f"Saving plan with ID {value} does not exist")

#     @validates("transaction_at")
#     def validate_transaction_date(self, value):
#         saving_plan_id = self.context.get("data", {}).get("saving_plan_id")
#         if not saving_plan_id:
#             return
#         saving_plan = TransactionValidator.get_saving_plan(
#             saving_plan_id, self.context.get("user_id")
#         )
#         if saving_plan:
#             if value.date() > saving_plan.current_deadline:
#                 raise ValidationError("Date exceeds saving plan deadline")
#             if value.date() < saving_plan.created_at.date():
#                 raise ValidationError("Date precedes saving plan creation")

#     @validates_schema
#     def validate_schema(self, data, **kwargs):
#         print("VALIDATING SCHEMA WITH DATA:", data)
#         validator = TransactionValidator
#         current_user = g.current_user
#         user_id = data.get("user_id", getattr(self.instance, "user_id", None))
#         self.context["user_id"] = UUID(user_id)
#         self.context["data"] = data
#         target_user = validator.get_user(user_id)
#         if not target_user:
#             raise ValidationError(f"User with ID {user_id} not found")
#         validator.validate_user_permissions(current_user, target_user)

#         self._process_uuid_fields(data)
#         self._validate_business_rules(data)

#     def _process_uuid_fields(self, data):
#         for field in ["category_id", "saving_plan_id"]:
#             if field in data and not data[field]:
#                 data[field] = None

#     def _validate_business_rules(self, data):
#         has_category = bool(data.get("category_id"))
#         has_saving_plan = bool(data.get("saving_plan_id"))

#         if has_category and has_saving_plan:
#             raise ValidationError(
#                 {"error": "Cannot have both category and saving plan"}
#             )
#         if not has_category and not has_saving_plan:
#             raise ValidationError({"error": "Must have either category or saving plan"})

#         if has_saving_plan and data["type"] == TransactionType.DEBIT:
#             raise ValidationError(
#                 {"type": "Debit transactions cannot use saving plans"}
#             )


# class TransactionSchema(BaseTransactionSchema):
#     class Meta(BaseTransactionSchema.Meta):
#         fields = (
#             "id",
#             "user_id",
#             "type",
#             "amount",
#             "category_id",
#             "saving_plan_id",
#             "description",
#             "transaction_at",
#             "created_at",
#             "updated_at",
#             "is_deleted",
#         )
#         dump_only = ("id", "created_at", "updated_at", "is_deleted")

#     transaction_at = fields.DateTime(format="%Y-%m-%d %H:%M:%S")

#     @post_load
#     def make_transaction(self, data, **kwargs):
#         """Convert validated data into a Transaction object."""
#         print("POST LOAD - INPUT DATA:", data)
#         if not self.instance:  # Creation case
#             transaction = Transaction(**data)
#             print("POST LOAD - CREATED TRANSACTION:", transaction)
#             print("POST LOAD - TRANSACTION TYPE:", type(transaction))
#             return transaction
#         print("POST LOAD - RETURNING DATA FOR UPDATE:", data)
#         return data


# class TransactionUpdateSchema(BaseTransactionSchema):
#     class Meta(BaseTransactionSchema.Meta):
#         fields = (
#             "type",
#             "amount",
#             "category_id",
#             "saving_plan_id",
#             "transaction_at",
#             "description",
#             "updated_at",
#         )
#         dump_only = ("updated_at",)

#     @validates_schema
#     def validate_update_schema(self, data, **kwargs):
#         super().validate_schema(data, **kwargs)
#         if self.instance:
#             self._validate_update_constraints(data)

#     def _validate_update_constraints(self, data):
#         current = self.instance
#         new_type = data.get("type")
#         new_category = data.get("category_id")
#         new_saving_plan = data.get("saving_plan_id")

#         if "category_id" in data or "saving_plan_id" in data:
#             if current.category_id and new_saving_plan:
#                 raise ValidationError(
#                     {"saving_plan_id": "Cannot switch to saving plan"}
#                 )
#             if current.saving_plan_id and new_category:
#                 raise ValidationError({"category_id": "Cannot switch to category"})

#         if new_type == TransactionType.DEBIT and (
#             new_saving_plan or current.saving_plan_id
#         ):
#             raise ValidationError({"type": "Cannot use DEBIT with saving plan"})
