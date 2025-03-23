from app.core.models import BaseModel
from app.extensions import db
from app.core.constants import Frequency, TransactionType
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar


class RecurringTransaction(BaseModel):
    __tablename__ = "recurring_transactions"

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    type = db.Column(db.Enum(TransactionType), nullable=False)
    frequency = db.Column(db.Enum(Frequency), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=True)
    next_transaction_at = db.Column(db.DateTime, nullable=False)
    category_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
    )
    saving_plan_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("saving_plans.id", ondelete="CASCADE"),
        nullable=True,
    )
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user = db.relationship(
        "User",
        backref=db.backref("recurring_transactions", lazy=True, cascade="all, delete"),
    )
    category = db.relationship(
        "Category",
        backref=db.backref("recurring_transactions", lazy=True, cascade="all, delete"),
    )
    saving_plan = db.relationship(
        "SavingPlan",
        backref=db.backref("recurring_transactions", lazy=True, cascade="all, delete"),
    )

    def get_next_run_date(self, current_date):
        """Calculate the next run date based on frequency"""
        if self.frequency == Frequency.DAILY:
            return current_date + relativedelta(days=1)
        elif self.frequency == Frequency.WEEKLY:
            return current_date + relativedelta(weeks=1)
        elif self.frequency == Frequency.MONTHLY:
            return self._calculate_monthly_next_run(current_date)
        elif self.frequency == Frequency.YEARLY:
            return self._calculate_yearly_next_run(current_date)
        return current_date

    def _calculate_monthly_next_run(self, current_date):
        """
        Calculate next monthly run date while preserving the original day when possible.
        Falls back to last day of month if original day doesn't exist in target month.
        """
        next_month = current_date + relativedelta(months=1)
        last_day_of_month = calendar.monthrange(next_month.year, next_month.month)[1]

        # Use the day from starts_at date, but don't exceed month's last day
        target_day = min(self.starts_at.day, last_day_of_month)

        return next_month.replace(day=target_day)

    def _calculate_yearly_next_run(self, current_date):
        """
        Calculate next yearly run date handling leap year edge cases.
        """
        next_year = current_date + relativedelta(years=1)

        # Handle February 29th special case
        if current_date.month == 2 and current_date.day == 29:
            try:
                return next_year.replace(month=2, day=29)
            except ValueError:
                return next_year.replace(month=2, day=28)

        return next_year
