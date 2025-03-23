import uuid
from datetime import datetime, timezone
from app.extensions import db


def get_utc_now():
    """Returns the current time in UTC with timezone awareness."""
    return datetime.now(timezone.utc)


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = db.Column(db.DateTime, default=get_utc_now)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
