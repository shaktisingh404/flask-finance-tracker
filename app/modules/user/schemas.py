import uuid
from marshmallow import (
    ValidationError,
    validates,
    fields,
    validates_schema,
    EXCLUDE,
    pre_load,
)

from enum import Enum
from app import ma, db
from app.modules.user.models import User
from app.core.validators import (
    validate_username,
    validate_email,
    validate_password,
    validate_name,
    validate_date_of_birth,
)
from app.core.constants import UserGender, UserRole
from app.core.schemas import BaseSchema


class UserSchema(BaseSchema):
    class Meta:
        model = User
        load_instance = True
        sqla_session = db.session
        load_only = ["password"]
        fields = [
            "id",
            "name",
            "username",
            "email",
            "password",
            "role",
            "date_of_birth",
            "gender",
            "created_at",
            "updated_at",
            "is_deleted",
        ]
        dump_only = (
            "id",
            "created_at",
            "updated_at",
            "role",
            "is_deleted",
        )
        unknown = EXCLUDE

    email = fields.Email(required=True, validate=validate_email)
    username = fields.String(required=True, validate=validate_username)
    name = fields.String(validate=validate_name)
    password = fields.String(required=True, load_only=True, validate=validate_password)
    role = fields.Enum(UserRole, by_value=True)
    date_of_birth = fields.Date(validate=validate_date_of_birth)
    gender = fields.Enum(UserGender, by_value=True)

    @pre_load
    def lowercase_email(self, data, **kwargs):
        if "email" in data:
            data["email"] = data["email"].lower()
        return data

    @validates("username")
    def validate_username(self, value):

        existing = User.query.filter_by(username=value).first()
        if existing and str(existing.id) != str(self.context.get("user_id", "")):
            raise ValidationError("Username already exists.")

    @validates("email")
    def validate_email(self, value):
        existing = User.query.filter_by(email=value).first()
        if existing and str(existing.id) != str(self.context.get("user_id", "")):
            raise ValidationError("Email already exists.")


class UserUpdateSchema(BaseSchema):
    """Base schema for user updates with validation"""

    username = fields.String(required=True, validate=validate_username)
    name = fields.String(required=True, validate=validate_name)
    date_of_birth = fields.Date(validate=validate_date_of_birth)
    gender = fields.Enum(UserGender, by_value=True)

    class Meta(BaseSchema.Meta):
        model = User
        fields = ("username", "name", "date_of_birth", "gender")
        include_fk = True

    @validates("username")
    def validate_username(self, value):
        """Validate username is unique"""
        # Get current instance
        instance = getattr(self, "instance", None)
        if instance and instance.username == value:
            return value
        user = User.query.filter_by(username=value).first()
        if user:
            raise ValidationError("Username already exists")
        return value


class PasswordUpdateSchema(ma.Schema):
    """Schema for updating user password"""

    current_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=validate_password)
    confirm_password = fields.String(required=True)

    @validates("current_password")
    def validate_current_password(self, value):
        """Validate that the current_password matches the target user's password"""
        # Access target_user from schema context
        target_user = self.context.get("target_user")
        if not target_user:
            raise ValidationError("User context not provided for validation")

        # Assuming User has a method like check_password (e.g., Werkzeug's check_password_hash)
        if not target_user.check_password(value):
            raise ValidationError("Current password is incorrect")

    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """Validate that new_password and confirm_password match"""
        if data.get("new_password") != data.get("confirm_password"):
            raise ValidationError("Passwords must match", "confirm_password")
        if data.get("new_password") == data.get("current_password"):
            raise ValidationError(
                "New password must be different from current password"
            )


class UserDeletionSchema(ma.Schema):
    """Schema for user account deletion"""

    password = fields.String(required=False)

    @validates_schema
    def validate(self, data, **kwargs):
        """Validate user account deletion"""
        current_user = self.context.get("current_user")
        is_staff = current_user.role == UserRole.ADMIN.value
        if not is_staff:
            password = data.get("password")
            if not password:
                raise ValidationError(
                    "Password is required to delete your account", "password"
                )
            if not current_user.check_password(password):
                raise ValidationError("Incorrect password", "password")
        return data


class EmailChangeRequestSchema(ma.Schema):
    """Schema for requesting email change with new email"""

    new_email = fields.Email(required=True, validate=validate_email)

    @validates("new_email")
    def validate_new_email(self, value):
        # Check if email already exists
        existing = User.query.filter_by(email=value).first()
        if existing:
            raise ValidationError("Email already exists")

        # Check if it's different from current email
        user = self.context.get("user")
        if user and user.email == value:
            raise ValidationError("New email must be different from your current email")

        return value


class EmailChangeConfirmSchema(ma.Schema):
    """Schema for confirming email change with two OTPs"""

    current_email_otp = fields.String(required=True)
    new_email_otp = fields.String(required=True)
