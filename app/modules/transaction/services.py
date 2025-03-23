from app import db
from app.modules.transaction.models import Transaction
from app.modules.saving_plan.models import SavingPlan
from decimal import Decimal
from sqlalchemy import extract
from app.modules.budget.models import Budget
from .models import Transaction
from app.core.logger import logger
from app.extensions import db
from app.modules.budget.tasks import check_budget_thresholds
from app.core.constants import TransactionType


class SavingPlanTransactionService:
    @staticmethod
    def get_saving_plan(saving_plan_id):
        """Find saving plan by id."""
        if not saving_plan_id:
            return None
        return SavingPlan.query.get(saving_plan_id)

    @staticmethod
    def update_saving_plan_on_transaction_created(transaction):
        """
        Update saving plan when a transaction is created.
        Args:
            transaction: Created Transaction object
        """
        try:
            if not transaction.saving_plan_id:
                return

            saving_plan = SavingPlanTransactionService.get_saving_plan(
                transaction.saving_plan_id
            )
            if saving_plan:
                saving_plan.saved_amount += transaction.amount
                db.session.commit()
                logger.info(
                    f"Updated saving plan {saving_plan.id} saved_amount after transaction created"
                )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating saving plan on transaction created: {str(e)}")
            raise e

    @staticmethod
    def update_saving_plan_on_transaction_updated(transaction, old_transaction):
        """
        Update saving plan when a transaction is updated.
        Args:
            transaction: Updated Transaction object
            old_transaction: Transaction object with pre-update values
        """
        try:
            # Check if saving plan or amount changed
            amount_changed = transaction.amount != old_transaction.amount
            plan_changed = transaction.saving_plan_id != old_transaction.saving_plan_id

            if not (amount_changed or plan_changed):
                return

            # Handle old saving plan
            if old_transaction.saving_plan_id:
                old_plan = SavingPlanTransactionService.get_saving_plan(
                    old_transaction.saving_plan_id
                )
                if old_plan:
                    old_plan.saved_amount -= old_transaction.amount
                    logger.info(
                        f"Reduced old saving plan {old_plan.id} saved_amount by {old_transaction.amount}"
                    )

            # Handle new saving plan
            if transaction.saving_plan_id:
                current_plan = SavingPlanTransactionService.get_saving_plan(
                    transaction.saving_plan_id
                )
                if current_plan:
                    current_plan.saved_amount += transaction.amount
                    logger.info(
                        f"Increased current saving plan {current_plan.id} saved_amount by {transaction.amount}"
                    )

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating saving plan on transaction updated: {str(e)}")
            raise e

    @staticmethod
    def update_saving_plan_on_transaction_deleted(transaction):
        """
        Update saving plan when a transaction is deleted.
        Args:
            transaction: Deleted Transaction object
        """
        try:
            if not transaction.saving_plan_id:
                return

            saving_plan = SavingPlanTransactionService.get_saving_plan(
                transaction.saving_plan_id
            )
            if saving_plan:
                saving_plan.saved_amount -= transaction.amount
                db.session.commit()
                logger.info(
                    f"Updated saving plan {saving_plan.id} saved_amount after transaction deleted"
                )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating saving plan on transaction deleted: {str(e)}")
            raise e


class BudgetTransactionService:
    @staticmethod
    def find_matching_budget(transaction):
        # Extract transaction date components
        txn_date = transaction.transaction_at
        month = txn_date.month
        year = txn_date.year
        # Find matching budget
        budget = Budget.query.filter(
            Budget.user_id == transaction.user_id,
            Budget.category_id == transaction.category_id,
            Budget.month == month,
            Budget.year == year,
            Budget.is_deleted == False,
        ).first()
        return budget

    @staticmethod
    def update_budget_on_transaction_created(transaction):

        try:
            budget = BudgetTransactionService.find_matching_budget(transaction)
            if not budget:
                logger.debug(f"No budget found for transaction {transaction.id}")
                return
            # Add transaction amount to budget spent_amount
            budget.spent_amount += transaction.amount
            db.session.commit()
            logger.info(
                f"Updated budget {budget.id} spent_amount after transaction created"
            )
            # Check if budget thresholds are reached
            check_budget_thresholds.delay(budget.id)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating budget on transaction created: {str(e)}")
            raise e

    @staticmethod
    def update_budget_on_transaction_updated(transaction, old_transaction):

        try:
            # Check if any relevant fields changed
            amount_changed = transaction.amount != old_transaction.amount
            category_changed = transaction.category_id != old_transaction.category_id
            date_changed = (
                transaction.transaction_at.month != old_transaction.transaction_at.month
                or transaction.transaction_at.year
                != old_transaction.transaction_at.year
            )
            # Skip if none of the relevant fields changed
            if not (amount_changed or category_changed or date_changed):
                return
            # Find the old budget
            old_budget = BudgetTransactionService.find_matching_budget(old_transaction)
            # Update the old budget if found
            if old_budget:
                old_budget.spent_amount -= old_transaction.amount
                logger.info(
                    f"Reduced old budget {old_budget.id} spent_amount by {old_transaction.amount}"
                )
            db.session.flush()
            # Find the current budget
            current_budget = BudgetTransactionService.find_matching_budget(transaction)
            if current_budget:
                # Add the new transaction amount
                current_budget.spent_amount += transaction.amount
                logger.info(
                    f"Increased current budget {current_budget.id} spent_amount by {transaction.amount}"
                )
            db.session.commit()
            if current_budget:
                check_budget_thresholds.delay(current_budget.id)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating budget on transaction updated: {str(e)}")
            raise e

    @staticmethod
    def update_budget_on_transaction_deleted(transaction):

        try:
            # Find matching budget
            budget = BudgetTransactionService.find_matching_budget(transaction)
            if not budget:
                logger.debug(
                    f"No budget found for deleted transaction {transaction.id}"
                )
                return
            # Subtract transaction amount from budget spent_amount
            budget.spent_amount -= transaction.amount
            db.session.commit()
            logger.info(
                f"Updated budget {budget.id} spent_amount after transaction deleted"
            )
            check_budget_thresholds.delay(budget.id)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating budget on transaction deleted: {str(e)}")
            raise e
