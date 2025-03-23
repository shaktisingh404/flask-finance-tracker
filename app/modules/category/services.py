from app.modules.category.models import Category
from app.core.logger import logger
from flask import abort
from app.extensions import db
from app.modules.transaction.models import Transaction
from app.modules.budget.models import Budget
from app.modules.recurring_transaction.models import RecurringTransaction


class CategoryService:
    """Service class for User-related operations."""

    @staticmethod
    def can_delete_category(category_id):
        has_transactions = Transaction.query.filter(
            Transaction.category_id == category_id, Transaction.is_deleted == False
        ).first()
        has_budgets = Budget.query.filter(
            Budget.is_deleted == False, Budget.category_id == category_id
        ).first()
        has_recurring_transactions = RecurringTransaction.query.filter(
            RecurringTransaction.category_id == category_id,
            RecurringTransaction.is_deleted == False,
        ).first()
        if has_transactions or has_budgets or has_recurring_transactions:
            return False
        return True
