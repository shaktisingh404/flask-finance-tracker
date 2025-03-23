from app.extensions import db
from app.core.models import BaseModel


class Category(BaseModel):

    __tablename__ = "categories"

    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_predefined = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship(
        "User", backref=db.backref("categories", lazy=True, cascade="all, delete")
    )

    def __repr__(self):
        return f"<Category {self.name}>"
