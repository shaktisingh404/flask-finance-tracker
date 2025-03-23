import uuid
from app.extensions import db, bcrypt
from app.core.models import BaseModel
from app.core.constants import UserRole, UserGender
from sqlalchemy import UniqueConstraint


class UserRelationship(db.Model):
    __tablename__ = "user_relationships"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_id = db.Column(
        db.UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False, index=True
    )
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)

    parent = db.relationship(
        "User",
        foreign_keys=[parent_id],
        backref=db.backref("child_relationships", uselist=True),
    )
    child = db.relationship(
        "User",
        foreign_keys=[child_id],
        backref=db.backref("parent_relationships", uselist=False),
    )
    __table_args__ = (
        UniqueConstraint(
            "parent_id", "child_id", name="unique_parent_child_relationship"
        ),
    )


class User(BaseModel):
    __tablename__ = "users"

    name = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    gender = db.Column(db.Enum(UserGender), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        """Hashes the password using Flask-Bcrypt before saving."""
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        """Checks the password hash."""
        return bcrypt.check_password_hash(self.password, password)

    def get_parent(self):
        """Returns the active parent user (non-deleted relationship)."""
        relation = UserRelationship.query.filter_by(
            child_id=self.id, is_deleted=False
        ).first()
        return relation.parent if relation else None

    def get_child(self):
        """Returns the active child user (non-deleted relationship)."""
        relation = UserRelationship.query.filter_by(
            parent_id=self.id, is_deleted=False
        ).first()
        return relation.child if relation else None
