from app.core.models import BaseModel
from app.extensions import db
from decimal import Decimal


class Budget(BaseModel):
    """Budget model."""

    __tablename__ = "budgets"
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    spent_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal(0.00))
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    warning_notification_sent = db.Column(db.Boolean, nullable=False, default=False)
    exceeded_notification_sent = db.Column(db.Boolean, nullable=False, default=False)
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )

    user = db.relationship("User", backref=db.backref("budgets", lazy="dynamic"))
    category = db.relationship(
        "Category", backref=db.backref("budgets", lazy="dynamic")
    )

    @property
    def remaining(self):
        """Calculate remaining budget"""
        return max(Decimal("0"), self.amount - self.spent_amount)

    @property
    def percentage_used(self):
        """Calculate percentage of budget used"""
        if self.amount == 0:
            return 100 if self.spent_amount > 0 else 0
        return min(100, int((self.spent_amount / self.amount) * 100))

    @property
    def is_exceeded(self):
        """Check if budget is exceeded"""
        return self.spent_amount > self.amount

    def set_notification_sent(self, notification_type: str) -> None:
        """Set the appropriate notification flag to True."""
        if notification_type == "warning":
            self.warning_notification_sent = True
        elif notification_type == "exceeded":
            self.exceeded_notification_sent = True
        db.session.commit()

    def reset_notification_flags(self, percentage_used: float) -> None:
        """Reset notification flags based on percentage used."""
        updated = False
        if percentage_used < 90 and self.warning_notification_sent:
            self.warning_notification_sent = False
            updated = True
        if percentage_used < 100 and self.exceeded_notification_sent:
            self.exceeded_notification_sent = False
            updated = True
        if updated:
            db.session.commit()

    def __repr__(self):
        return f"<Budget {self.id}: {self.user_id} | {self.category_id} | {self.month}/{self.year}>"
