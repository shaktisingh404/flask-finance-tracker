from app.core.models import BaseModel
from app.extensions import db
from app.core.constants import TransactionType
from app.modules.saving_plan.models import SavingPlan


class Transaction(BaseModel):
    __tablename__ = "transactions"
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    type = db.Column(db.Enum(TransactionType), nullable=False)
    transaction_at = db.Column(db.DateTime, nullable=False)
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
        "User", backref=db.backref("transactions", lazy=True, cascade="all, delete")
    )
    category = db.relationship(
        "Category", backref=db.backref("transactions", lazy=True, cascade="all, delete")
    )
    saving_plan = db.relationship(
        "SavingPlan",
        backref=db.backref("transactions", lazy=True, cascade="all, delete"),
    )

    def __str__(self):
        return f"Transaction(type={self.type}, amount={self.amount})"
