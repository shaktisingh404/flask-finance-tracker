from marshmallow import (
    Schema,
    fields,
    validate,
    validates,
    ValidationError,
    EXCLUDE,
    validates_schema,
)
from app.extensions import ma
from app.modules.auth.models import ActiveAccessToken
from app.modules.user.models import User
from app.core.validators import (
    validate_email,
    validate_password,
)
from app.core.schemas import BaseSchema


class UserAuthSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = User
        exclude = ("password",)


class UserLoginSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)

    class Meta:
        unknown = EXCLUDE


class PasswordResetRequestSchema(ma.Schema):
    email = fields.Email(required=True, validate=validate_email)

    @validates("email")
    def validate_email(self, value):
        user = User.query.filter_by(
            email=value, is_deleted=False, is_verified=True
        ).first()
        if not user:
            raise ValidationError("No user found with this email address.")
        return value


class PasswordResetConfirmSchema(ma.Schema):
    password = fields.String(required=True, validate=validate_password)
    confirm_password = fields.String(required=True)

    @validates_schema
    def validate_passwords(self, data, **kwargs):
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError("Passwords must match", "confirm_password")


class ResendVerificationSchema(ma.Schema):
    email = fields.Email(required=True, validate=validate_email)
