# from flask_restful import Resource
# from flask import request, g
# from marshmallow import ValidationError

# from app.extensions import db
# from app.models.budget import Budget
# from app.schemas.budget import budget_schema, budgets_schema, budget_update_schema
# from app.services.budget import (
#     get_user_budgets,
#     create_budget,
#     update_budget,
# )
# from app.utils.permissions import authenticated_user, object_permission
# from app.utils.responses import validation_error_response
# from app.utils.pagination import paginate
# from app.utils.logger import logger


# class BudgetListResource(Resource):
#     """Resource for listing and creating budgets"""

#     method_decorators = [authenticated_user]

#     def get(self):
#         """
#         Get budgets based on user role with optional filtering.
#         Query parameters:
#         - user_id: For admin to filter by specific user
#         - child_id: For regular users to filter by their child
#         - category_id: Filter by specific category
#         - month: Filter by month (1-12)
#         - year: Filter by year
#         """
#         try:
#             # Get authenticated user info
#             user = g.user
#             user_role = g.role

#             query_params = {
#                 "user_id": request.args.get("user_id"),
#                 "child_id": request.args.get("child_id"),
#                 "category_id": request.args.get("category_id"),
#                 "month": request.args.get("month"),
#                 "year": request.args.get("year"),
#             }

#             logger.info(f"Budget list requested by user {user.id}")

#             query = get_user_budgets(user, user_role, query_params)

#             # Return paginated response
#             result = paginate(
#                 query=query,
#                 schema=budgets_schema,
#                 endpoint="budget.budgets",
#             )
#             return result, 200

#         except ValidationError as err:
#             return validation_error_response(err)

#     def post(self):
#         """
#         Create a new budget.
#         """
#         try:
#             data = request.get_json() or {}

#             logger.info("Creating budget")

#             budget = budget_schema.load(data)

#             # Create budget through service
#             budget = create_budget(budget)

#             if isinstance(budget, tuple) and len(budget) == 2:
#                 return budget

#             return budget_schema.dump(budget), 201

#         except ValidationError as err:
#             return validation_error_response(err)


# class BudgetDetailResource(Resource):
#     """
#     Resource for retrieving, updating and deleting a specific budget
#         -ADMIN can view, update and delete any budget
#         -USER can view, update and delete their own budgets and can view its child budgets
#         -CHILD can view, update and delete their own budgets
#     """

#     method_decorators = [
#         object_permission(Budget),
#         authenticated_user,
#     ]

#     def get(self, id):
#         """
#         Get a specific budget.
#         """
#         budget = g.object  # Already has permission checked
#         result = budget_schema.dump(budget)
#         logger.info(f"Retrieved budget {budget.id}")
#         return result, 200

#     def patch(self, id):
#         """
#         Update a specific budget(only amount of the budget can be updated).
#         """
#         try:
#             budget = g.object  # Already has permission checked
#             data = request.get_json() or {}
#             old_amount = budget.amount

#             logger.info(f"Updating budget {budget.id}")

#             updated_budget = budget_update_schema.load(
#                 data, instance=budget, partial=True
#             )

#             budget = update_budget(updated_budget, old_amount)

#             if isinstance(budget, tuple) and len(budget) == 2:
#                 return budget

#             logger.info(f"Updated budget {budget.id}")
#             return budget_schema.dump(budget), 200

#         except ValidationError as err:
#             return validation_error_response(err)

#     def delete(self, id):
#         """
#         Delete (soft-delete) a specific budget.
#         """
#         budget = g.object  # Already has permission checked

#         budget.is_deleted = True
#         db.session.commit()

#         logger.info(f"Deleted budget {budget.id}")
#         return "", 204


# # model

# from decimal import Decimal
# from datetime import date, timedelta
# from app.extensions import db
# from app.models.base import BaseModel


# class Budget(BaseModel):
#     """Model for budget table"""

#     __tablename__ = "budgets"

#     amount = db.Column(db.Numeric(10, 2), nullable=False)
#     spent_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal(0.00))

#     month = db.Column(db.Integer, nullable=False)
#     year = db.Column(db.Integer, nullable=False)

#     user_id = db.Column(
#         db.UUID(as_uuid=True),
#         db.ForeignKey("users.id", ondelete="CASCADE"),
#         nullable=False,
#     )
#     category_id = db.Column(
#         db.UUID(as_uuid=True),
#         db.ForeignKey("categories.id", ondelete="CASCADE"),
#         nullable=False,
#     )

#     # Relationship
#     user = db.relationship("User", backref=db.backref("budgets", lazy="dynamic"))
#     category = db.relationship(
#         "Category", backref=db.backref("budgets", lazy="dynamic")
#     )

#     @property
#     def remaining(self):
#         """Calculate remaining budget"""
#         return max(Decimal("0"), self.amount - self.spent_amount)

#     @property
#     def percentage_used(self):
#         """Calculate percentage of budget used"""
#         if self.amount == 0:
#             return 100 if self.spent_amount > 0 else 0
#         return min(100, int((self.spent_amount / self.amount) * 100))

#     @property
#     def is_exceeded(self):
#         """Check if budget is exceeded"""
#         return self.spent_amount > self.amount

#     def __repr__(self):
#         return f"<Budget {self.id}: {self.user_id} | {self.category_id} | {self.month}/{self.year}>"


# schema

# from marshmallow import fields, validates, validates_schema, ValidationError, EXCLUDE
# from marshmallow.validate import Range
# from app.extensions import ma
# from app.models.budget import Budget
# from app.models.category import Category
# from app.models.user import User
# from app.utils.constants import UserRole, AMOUNT_MIN_VALUE, AMOUNT_MAX_VALUE
# from flask import g
# from decimal import Decimal
# import datetime


# class BudgetSchema(ma.SQLAlchemyAutoSchema):
#     """Schema for Budget model - used for creation and reading"""

#     class Meta:
#         model = Budget
#         load_instance = True
#         include_fk = True
#         fields = (
#             "id",
#             "user_id",
#             "category_id",
#             "amount",
#             "spent_amount",
#             "month",
#             "year",
#             "is_deleted",
#             "created_at",
#             "updated_at",
#         )
#         dump_only = (
#             "id",
#             "spent_amount",
#             "is_deleted",
#             "created_at",
#             "updated_at",
#         )
#         unknown = EXCLUDE

#     # Validation for fields
#     amount = fields.Decimal(
#         required=True,
#         places=2,
#         as_string=True,
#         validate=Range(min=AMOUNT_MIN_VALUE, max=AMOUNT_MAX_VALUE),
#     )
#     spent_amount = fields.Decimal(places=2, as_string=True, dump_only=True)

#     @validates("user_id")
#     def validate_user_id(self, value):
#         """
#         Validate that:
#         1. The user exists and is not deleted
#         2. The current user has permission to create budgets for this user
#         """
#         target_user = User.query.get(value)
#         if not target_user or target_user.is_deleted:
#             raise ValidationError("User not found")

#         # Check permissions
#         current_user = g.user
#         current_user_role = g.role

#         if current_user_role == UserRole.ADMIN.value:
#             if target_user.role.value == UserRole.ADMIN.value:
#                 raise ValidationError("Admin users cannot have budgets")
#             return value

#         else:
#             if str(value) != str(current_user.id):
#                 raise ValidationError("You can only create budgets for yourself")
#             return value

#     @validates("category_id")
#     def validate_category_id(self, value):
#         """Validate category exists and is not deleted"""
#         category = Category.query.get(value)
#         if not category or category.is_deleted:
#             raise ValidationError("Category not found")
#         return value

#     @validates("month")
#     def validate_month(self, value):
#         """Validate month is between 1-12"""
#         if not 1 <= value <= 12:
#             raise ValidationError("Month must be between 1 and 12")
#         return value

#     @validates("year")
#     def validate_year(self, value):
#         """Validate year is reasonable (not too far in past or future)"""
#         current_year = datetime.datetime.now().year
#         if not (current_year - 5) <= value <= (current_year + 5):
#             raise ValidationError(
#                 f"Year must be between {current_year-5} and {current_year+5}"
#             )
#         return value

#     @validates_schema
#     def validate_unique_budget(self, data, **kwargs):
#         """
#         Validate uniqueness: one budget per user-category-month-year
#         """

#         user_id = data["user_id"]
#         category_id = data["category_id"]
#         month = data["month"]
#         year = data["year"]

#         category = Category.query.get(category_id)
#         if not category or category.is_deleted:
#             raise ValidationError("Category not found", "category_id")

#         # Query for existing budget
#         existing = Budget.query.filter(
#             Budget.user_id == user_id,
#             Budget.category_id == category_id,
#             Budget.month == month,
#             Budget.year == year,
#             Budget.is_deleted == False,
#         ).first()

#         if existing:
#             raise ValidationError(
#                 "A budget already exists for this user, category, month and year",
#                 "month_year",
#             )


# class BudgetUpdateSchema(ma.SQLAlchemyAutoSchema):
#     """Schema for updating Budget - only amount can be changed"""

#     class Meta:
#         model = Budget
#         load_instance = True
#         include_fk = True
#         fields = ("amount",)
#         unknown = EXCLUDE

#     amount = fields.Decimal(
#         required=True,
#         places=2,
#         as_string=True,
#         validate=Range(min=AMOUNT_MIN_VALUE, max=AMOUNT_MAX_VALUE),
#     )


# # Create schema instances
# budget_schema = BudgetSchema()
# budgets_schema = BudgetSchema(many=True)
# budget_update_schema = BudgetUpdateSchema()

# services
# from app.models.budget import Budget
# from app.utils.logger import logger
# from app.extensions import db
# from app.services.common import fetch_standard_resources
# from datetime import datetime
# from decimal import Decimal
# from app.utils.validators import is_valid_uuid
# from marshmallow import ValidationError
# from sqlalchemy import extract
# from app.models.transaction import Transaction
# from app.utils.constants import TransactionType, MIN_YEAR, MAX_YEAR
# from app.tasks.budget import check_budget_thresholds


# def get_user_budgets(user, role, query_params=None):
#     """
#     Get budgets based on user role and query parameters.

#     Args:
#         user: The user requesting budgets
#         role: The role of the requesting user
#         query_params: Dict with optional filters:
#             - user_id: For ADMIN to filter by specific user
#             - child_id: For USER to filter by their child
#             - category_id: Filter by specific category
#             - month: Filter by month (1-12)
#             - year: Filter by year
#     """
#     if query_params is None:
#         query_params = {}

#     # Get base query with standard role-based filtering
#     query = fetch_standard_resources(
#         model_class=Budget,
#         user=user,
#         role=role,
#         query_params=query_params,
#     )

#     # Apply additional filters
#     if "category_id" in query_params and query_params["category_id"]:
#         category_id = query_params["category_id"]

#         if is_valid_uuid(category_id):
#             query = query.filter(Budget.category_id == category_id)
#         else:
#             raise ValidationError(f"Invalid category_id format {category_id}")

#     if "month" in query_params and query_params["month"]:
#         if "year" not in query_params or not query_params["year"]:
#             raise ValidationError(
#                 "Filtering by month requires specifying a year as well."
#             )

#         try:
#             month = int(query_params["month"])
#             year = int(query_params["year"])

#             if not (1 <= month <= 12):
#                 raise ValidationError("Month must be between 1 and 12")

#             if not (MIN_YEAR <= year <= MAX_YEAR):
#                 raise ValidationError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}")

#             query = query.filter(Budget.month == month, Budget.year == year)
#         except (ValueError, TypeError):
#             logger.warning(f"Invalid month/year parameters: {query_params}")
#             raise ValidationError("Invalid month or year format.")

#     elif "year" in query_params and query_params["year"]:
#         try:
#             year = int(query_params["year"])

#             if not (MIN_YEAR <= year <= MAX_YEAR):
#                 raise ValidationError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}")

#             query = query.filter(Budget.year == year)
#         except (ValueError, TypeError):
#             logger.warning(f"Invalid year parameter: {query_params['year']}")
#             raise ValidationError("Invalid year format.")

#     # Apply default ordering (by year desc, month desc)
#     query = query.order_by(Budget.year.desc(), Budget.month.desc())

#     return query


# def create_budget(budget):
#     """
#     Create a new budget with initial spent amount calculation
#     """
#     try:
#         # Calculate existing spending for this month/year/category
#         spent_amount = calculate_month_spending(
#             budget.user_id, budget.category_id, budget.month, budget.year
#         )

#         # Set the calculated spent amount
#         budget.spent_amount = spent_amount

#         db.session.add(budget)
#         db.session.commit()

#         logger.info(
#             f"Created budget {budget.id} for {budget.user_id}, {budget.category_id}, {budget.month}/{budget.year} with initial spent_amount {spent_amount}"
#         )

#         # Queue Celery task to check if budget already exceeding thresholds
#         check_budget_thresholds.delay(budget.id)

#         return budget

#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error creating budget: {str(e)}")
#         return {"error": f"Failed to create budget: {str(e)}"}, 500


# def update_budget(updated_budget, old_amount):
#     """Update a budget amount"""
#     try:
#         new_amount = updated_budget.amount
#         db.session.commit()
#         if new_amount != old_amount:
#             # Queue Celery task to check if budget already exceeding thresholds
#             check_budget_thresholds.delay(updated_budget.id)
#         return updated_budget

#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error updating budget: {str(e)}")
#         return {"error": f"Failed to update budget: {str(e)}"}, 500


# def calculate_month_spending(user_id, category_id, month, year):
#     """
#     Calculate total spending for a specific month/year/category

#     Args:
#         user_id: User ID
#         category_id: Category ID
#         month: Month (1-12)
#         year: Year

#     Returns:
#         Decimal: Total spending amount
#     """
#     # Query for transactions in the given month/year for this category and user
#     transactions = Transaction.query.filter(
#         Transaction.user_id == user_id,
#         Transaction.category_id == category_id,
#         extract("month", Transaction.transaction_at) == month,
#         extract("year", Transaction.transaction_at) == year,
#         Transaction.is_deleted == False,
#         Transaction.type == TransactionType.DEBIT,  # Only count expense transactions
#     ).all()

#     # Sum up the amounts
#     total = Decimal("0.00")
#     for transaction in transactions:
#         total += transaction.amount

#     return total


# urls

# from flask import Blueprint
# from flask_restful import Api
# from app.resources.budget import (
#     BudgetListResource,
#     BudgetDetailResource,
# )

# budget_bp = Blueprint("budget", __name__)
# budget_api = Api(budget_bp)

# # Register endpoints
# budget_api.add_resource(BudgetListResource, "", endpoint="budgets")
# budget_api.add_resource(BudgetDetailResource, "/<id>", endpoint="budget-detail")

# tasks

# from app.extensions import db
# from app.utils.logger import logger
# from app.celery_app import celery
# from app.utils.constants import BUDGET_WARNING_THRESHOLD, BUDGET_EXCEEDED_THRESHOLD
# from app.models.budget import Budget
# from app.models.user import User
# from app.models.category import Category
# from app.utils.email_helper import send_templated_email
# from decimal import Decimal
# import calendar


# @celery.task(name="check_budget_thresholds", bind=True, max_retries=3)
# def check_budget_thresholds(self, budget_id):
#     """
#     Check if budget has reached/exceeded thresholds and send notifications.

#     Args:
#         budget_id: ID of the budget to check.
#     """
#     try:
#         budget = Budget.query.get(budget_id)
#         if not budget:
#             logger.warning(f"Budget not found for threshold check: {budget_id}")
#             return False

#         percentage_used = budget.percentage_used

#         # Determine the notification type
#         if percentage_used >= BUDGET_EXCEEDED_THRESHOLD:
#             notification_type = "exceeded"
#         elif percentage_used >= BUDGET_WARNING_THRESHOLD:
#             notification_type = "warning"
#         else:
#             return False  # No notification needed

#         logger.info(
#             f"Budget {budget.id} {notification_type} threshold reached: {percentage_used}%"
#         )

#         # Send budget notification
#         send_budget_notification.delay(budget.id, notification_type, percentage_used)

#         return True

#     except Exception as e:
#         logger.error(f"Error checking budget thresholds: {str(e)}")
#         if self.request.retries < self.max_retries:
#             self.retry(exc=e, countdown=60 * (self.request.retries + 1))
#         return False


# @celery.task(name="send_budget_notification", bind=True, max_retries=3)
# def send_budget_notification(self, budget_id, notification_type, percentage=None):
#     """
#     Send a budget notification (warning or exceeded).

#     Args:
#         budget_id: ID of the budget.
#         notification_type: Either "warning" or "exceeded".
#         percentage: Optional specific percentage to mention.
#     """
#     try:
#         budget = Budget.query.get(budget_id)
#         if not budget:
#             logger.warning(
#                 f"Budget not found for {notification_type} notification: {budget_id}"
#             )
#             return False

#         user = User.query.get(budget.user_id)
#         if not user or not user.email:
#             logger.warning(f"User not found or no email for budget {budget_id}")
#             return False

#         category = Category.query.get(budget.category_id)
#         if not category:
#             logger.warning(f"Category not found for budget {budget_id}")
#             return False

#         # Get month name dynamically
#         month_name = calendar.month_name[budget.month]

#         # Default to actual percentage if not provided
#         percentage = percentage or budget.percentage_used

#         email_data = {
#             "recipient": user.email,
#             "category_name": category.name,
#             "month_name": month_name,
#             "year": budget.year,
#             "budget_amount": float(budget.amount),
#             "spent_amount": float(budget.spent_amount),
#         }

#         # Customize email subject & template based on notification type
#         if notification_type == "warning":
#             email_data.update(
#                 {
#                     "subject": f"Budget Warning: {category.name} budget is at {percentage}%",
#                     "template": "emails/budget/warning.html",
#                     "remaining": float(budget.remaining),
#                     "percentage": percentage,
#                 }
#             )
#         elif notification_type == "exceeded":
#             email_data.update(
#                 {
#                     "subject": f"Budget Alert: {category.name} budget has been exceeded!",
#                     "template": "emails/budget/exceeded.html",
#                     "overspent": float(
#                         max(Decimal("0"), budget.spent_amount - budget.amount)
#                     ),
#                 }
#             )
#         else:
#             logger.error(f"Invalid notification type: {notification_type}")
#             return False

#         # Send templated email
#         send_templated_email(**email_data)

#         logger.info(
#             f"Sent budget {notification_type} notification to {user.email} for budget {budget_id}"
#         )
#         return True

#     except Exception as e:
#         logger.error(f"Error sending budget {notification_type} notification: {str(e)}")
#         if self.request.retries < self.max_retries:
#             self.retry(exc=e, countdown=60 * (self.request.retries + 1))
#         return False


# # transactions

# from decimal import Decimal
# from sqlalchemy import extract
# from app.models.budget import Budget
# from app.models.transaction import Transaction
# from app.utils.logger import logger
# from app.extensions import db
# from app.tasks.budget import check_budget_thresholds
# from app.utils.constants import TransactionType


# def find_matching_budget(transaction):
#     """
#     Find a budget matching a transaction's user, category, month and year.
#     Args:
#         transaction: Transaction object
#     Returns:
#         Budget object or None if no matching budget found
#     """
#     # Extract transaction date components
#     txn_date = transaction.transaction_at
#     month = txn_date.month
#     year = txn_date.year
#     # Find matching budget
#     budget = Budget.query.filter(
#         Budget.user_id == transaction.user_id,
#         Budget.category_id == transaction.category_id,
#         Budget.month == month,
#         Budget.year == year,
#         Budget.is_deleted == False,
#     ).first()
#     return budget


# def update_budget_on_transaction_created(transaction):
#     """
#     Update budget when a transaction is created.
#     Args:
#         transaction: Created Transaction object
#     """
#     try:
#         budget = find_matching_budget(transaction)
#         if not budget:
#             logger.debug(f"No budget found for transaction {transaction.id}")
#             return
#         # Add transaction amount to budget spent_amount
#         budget.spent_amount += transaction.amount
#         db.session.commit()
#         logger.info(
#             f"Updated budget {budget.id} spent_amount after transaction created"
#         )
#         # Check if budget thresholds are reached
#         check_budget_thresholds.delay(budget.id)
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error updating budget on transaction created: {str(e)}")
#         raise e


# def update_budget_on_transaction_updated(transaction, old_transaction):
#     """
#     Update budget when a transaction is updated.
#     Args:
#         transaction: Updated Transaction object
#         old_transaction: Transaction object with pre-update values
#     """
#     try:
#         # Check if any relevant fields changed
#         amount_changed = transaction.amount != old_transaction.amount
#         category_changed = transaction.category_id != old_transaction.category_id
#         date_changed = (
#             transaction.transaction_at.month != old_transaction.transaction_at.month
#             or transaction.transaction_at.year != old_transaction.transaction_at.year
#         )
#         # Skip if none of the relevant fields changed
#         if not (amount_changed or category_changed or date_changed):
#             return
#         # Find the old budget
#         old_budget = find_matching_budget(old_transaction)
#         # Update the old budget if found
#         if old_budget:
#             old_budget.spent_amount -= old_transaction.amount
#             logger.info(
#                 f"Reduced old budget {old_budget.id} spent_amount by {old_transaction.amount}"
#             )
#         db.session.flush()
#         # Find the current budget
#         current_budget = find_matching_budget(transaction)
#         if current_budget:
#             # Add the new transaction amount
#             current_budget.spent_amount += transaction.amount
#             logger.info(
#                 f"Increased current budget {current_budget.id} spent_amount by {transaction.amount}"
#             )
#         db.session.commit()
#         if current_budget:
#             check_budget_thresholds.delay(current_budget.id)
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error updating budget on transaction updated: {str(e)}")
#         raise e


# def update_budget_on_transaction_deleted(transaction):
#     """
#     Update budget when a transaction is deleted.
#     Args:
#         transaction: Deleted Transaction object
#     """
#     try:
#         # Find matching budget
#         budget = find_matching_budget(transaction)
#         if not budget:
#             logger.debug(f"No budget found for deleted transaction {transaction.id}")
#             return
#         # Subtract transaction amount from budget spent_amount
#         budget.spent_amount -= transaction.amount
#         db.session.commit()
#         logger.info(
#             f"Updated budget {budget.id} spent_amount after transaction deleted"
#         )
#         check_budget_thresholds.delay(budget.id)
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error updating budget on transaction deleted: {str(e)}")
#         raise e
