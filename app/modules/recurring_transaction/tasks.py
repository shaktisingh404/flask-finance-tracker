import os
from app.celery_app import celery
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from app.extensions import db
from app.core.logger import logger
from app.modules.transaction.models import Transaction
from app.modules.recurring_transaction.models import RecurringTransaction
from app.modules.saving_plan.models import SavingPlan
from app.modules.budget.tasks import check_budget_thresholds
from app.core.mail import send_email
from typing import Dict, Any
from app.modules.transaction.services import (
    update_budget_on_transaction_created,
    update_saving_plan_on_transaction_created,
)
from datetime import timezone
from app.core.constants import TransactionType

SENDGRID_SAVINGS_PLAN_COMPLETION_TEMPLATE_ID = os.getenv("SAVING_PLAN_COMPLETED")
SENDGRID_RECURRING_TRANSACTION_TEMPLATE_ID = os.getenv(
    "RECURRING_TRANSACTION_TEMPLATE_ID"
)


@celery.task(name="send_transaction_notification", bind=True, max_retries=3)
def send_transaction_notification(
    self,  # Add self parameter for bound task
    user_email: str,
    subject: str,
    template_data: Dict[str, Any],
    template_id: str,
) -> None:
    """Send transaction email notification with retry logic"""
    try:
        send_email(
            to_email=user_email,
            subject=subject,  # Use the passed subject parameter
            template_data=template_data,
            template_id=template_id,
        )
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}", exc_info=True)
        raise self.retry(exc=e)  # Use self.retry for bound task


@celery.task(bind=True)
def process_recurring_transactions(self):
    """Process daily recurring transactions - Runs once per day"""
    try:
        now = datetime.now(timezone.utc)

        recurring_transactions = (
            RecurringTransaction.query.join(RecurringTransaction.user)
            .join(RecurringTransaction.category, isouter=True)
            .join(RecurringTransaction.saving_plan, isouter=True)
            .filter(
                RecurringTransaction.next_transaction_at <= now,
                RecurringTransaction.is_deleted == False,
            )
            .all()
        )

        logger.info(f"Current time: {now}")
        logger.info(f"Found {len(recurring_transactions)} recurring transactions")
        for rec_txn in recurring_transactions:
            logger.info(
                f"Transaction ID: {rec_txn.id}, Next run: {rec_txn.next_transaction_at}"
            )
            try:
                if not _is_transaction_valid(rec_txn):
                    rec_txn.is_deleted = True
                    db.session.commit()
                    continue

                # Create new transaction
                new_transaction = _create_transaction(rec_txn)
                db.session.add(new_transaction)
                db.session.flush()

                # Update budget

                # Handle category or savings plan
                if rec_txn.category_id and rec_txn.type == TransactionType.DEBIT.value:
                    check_budget_thresholds.delay(new_transaction.id)
                    update_budget_on_transaction_created(new_transaction)
                elif rec_txn.saving_plan_id:
                    update_saving_plan_on_transaction_created(rec_txn, new_transaction)

                # Update next run date
                rec_txn.next_transaction_at = rec_txn.get_next_run_date(
                    rec_txn.next_transaction_at
                )
                db.session.commit()

                # Send notification
                send_transaction_notification.delay(
                    rec_txn.user.email,
                    "Recurring Transaction Created",
                    {
                        "subject": "Recurring Transaction",
                        "transaction_amount": f"{float(rec_txn.amount):.2f}",
                        "transaction_date": rec_txn.next_transaction_at.strftime(
                            "%Y-%m-%d"
                        ),
                        "description": rec_txn.description or "No description provided",
                    },
                    SENDGRID_RECURRING_TRANSACTION_TEMPLATE_ID,
                )

            except Exception as e:
                db.session.rollback()
                logger.error(
                    f"Error processing recurring transaction {rec_txn.id}: {str(e)}",
                    exc_info=True,
                )
                continue  # Continue to next transaction instead of failing the whole task

    except Exception as e:
        logger.error(
            f"Error processing recurring transactions: {str(e)}", exc_info=True
        )
        raise self.retry(exc=e)  # Retry the entire task on fatal error


def _is_transaction_valid(rec_txn: RecurringTransaction) -> bool:
    """Check if the recurring transaction is valid for processing"""
    return (
        not (rec_txn.user.is_deleted)
        and not (rec_txn.category and rec_txn.category.is_deleted)
        and not (rec_txn.saving_plan and rec_txn.saving_plan.is_deleted)
        and not (rec_txn.ends_at and rec_txn.ends_at < rec_txn.next_transaction_at)
    )


def _create_transaction(rec_txn: RecurringTransaction) -> Transaction:
    """Create a new transaction for the recurring transaction"""
    return Transaction(
        user_id=rec_txn.user_id,
        category_id=rec_txn.category_id,
        saving_plan_id=rec_txn.saving_plan_id,
        type=rec_txn.type,
        amount=rec_txn.amount,
        transaction_at=rec_txn.next_transaction_at,
        description=rec_txn.description,
    )


# def _process_savings_plan(
#     rec_txn: RecurringTransaction, transaction: Transaction
# ) -> None:
#     """Process a savings plan transaction"""
#     saving_plan = rec_txn.saving_plan
#     total_saved = db.session.query(func.sum(Transaction.amount)).filter(
#         Transaction.saving_plan_id == saving_plan.id, Transaction.is_deleted == False
#     ).scalar() or Decimal("0")

#     # Add new transaction amount to total saved
#     total_saved += transaction.amount

#     SavingsPlanManager.update_status(saving_plan, total_saved)  # Use the static method

# class SavingsPlanManager:
#     @staticmethod
#     def update_status(plan: SavingPlan, total_saved: Decimal) -> None:
#         """Update savings plan status and notify user if completed"""
#         if total_saved >= plan.target_amount and plan.status != "COMPLETED":
#             plan.status = "COMPLETED"
#             db.session.commit()

#             notification_data = {
#                 "user_name": plan.user.name,
#                 "savings_plan_name": plan.name,
#                 "total_saved": f"{float(total_saved):,.2f}",
#                 "target_amount": f"{float(plan.target_amount):,.2f}",
#                 "message": f"Congratulations! Your savings plan '{plan.name}' has been completed!",
#             }

#             send_transaction_notification.delay(
#                 plan.user.email,
#                 "Savings Plan Completed",
#                 notification_data,
#                 os.get.SENDGRID_SAVINGS_PLAN_COMPLETION_TEMPLATE_ID,
#             )
