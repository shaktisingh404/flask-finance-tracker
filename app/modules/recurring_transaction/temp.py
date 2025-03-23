from datetime import datetime
from .models import RecurringTransaction
from sqlalchemy.orm import joinedload


def process_recurring_transactions(self):
    """Process daily recurring transactions - Runs once per day"""

    now = datetime.utcnow()

    # Update joinedload to use class attributes
    recurring_transactions = (
        RecurringTransaction.query.options(
            joinedload(RecurringTransaction.user),
            joinedload(RecurringTransaction.category),
            joinedload(RecurringTransaction.saving_plan),
        )
        .filter(
            RecurringTransaction.next_transaction_at <= now,
            RecurringTransaction.is_deleted == False,
        )
        .all()
    )
