from app.core.models import BaseModel
from app.extensions import db
from app.core.constants import SavingPlanStatus, Frequency
from decimal import Decimal


class SavingPlan(BaseModel):
    __tablename__ = "saving_plans"

    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    original_deadline = db.Column(db.Date, nullable=False)
    current_deadline = db.Column(db.Date, nullable=False)
    saved_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal(0.00))
    status = db.Column(
        db.Enum(SavingPlanStatus), nullable=False, default=SavingPlanStatus.ACTIVE
    )
    frequency = db.Column(db.Enum(Frequency), nullable=False)
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user = db.relationship(
        "User", backref=db.backref("saving_plans", lazy=True, cascade="all, delete")
    )
