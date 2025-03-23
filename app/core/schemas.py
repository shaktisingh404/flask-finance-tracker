from app.extensions import ma
from marshmallow import EXCLUDE
from app.extensions import db


class BaseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
