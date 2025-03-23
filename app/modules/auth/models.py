# app/modules/auth/models.py
from app.extensions import db
from datetime import datetime
from app.core.models import BaseModel
from sqlalchemy import Text


class ActiveAccessToken(BaseModel):
    __tablename__ = "active_access_tokens"

    token = db.Column(Text, unique=True, nullable=False)  # Stores JWT
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    expires_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship(
        "User", backref=db.backref("tokens", lazy=True, cascade="all, delete")
    )

    def __repr__(self):
        return f"<ActiveAccessToken {self.token[:10]}... for User {self.user_id}>"
