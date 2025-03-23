from flask_restful import Resource
from flask import request, g
from marshmallow import ValidationError
from app.extensions import db
from app.modules.user.schemas import (
    UserSchema,
    PasswordUpdateSchema,
    UserUpdateSchema,
    UserDeletionSchema,
    EmailChangeConfirmSchema,
    EmailChangeRequestSchema,
)
from app.modules.user.services import (
    UserService,
    EmailChangeService,
    StaffEmailChangeService,
)
from app.modules.user.models import User
from app.core.permissions import (
    permission_required,
    admin_only,
    prevent_child_creation,
    admin_or_self,
)
from app.core.decorators import validate_json_request
from app.core.authentication import authenticated_user
from app.core.responses import validation_error_response
from app.core.logger import logger
from app.core.pagination import paginate
from app.modules.user.tasks import send_staff_email_verification, delete_associated_data
from flask import url_for
from app.core.decorators import handle_errors
from app.core.utils import BaseListResource

# Initialize schemas once
user_schema = UserSchema()
users_schema = UserSchema(many=True)
password_update_schema = PasswordUpdateSchema()
user_delete_schema = UserDeletionSchema()
user_update_schema = UserUpdateSchema()
email_change_confirm_schema = EmailChangeConfirmSchema()
email_change_request_schema = EmailChangeRequestSchema()


def get_json_data():
    """Helper to safely get JSON data from request."""
    return request.get_json() or {}


def get_bearer_token():
    """Extract bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    return auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None


class UserListResource(BaseListResource):
    method_decorators = [
        admin_only,
        authenticated_user,
    ]
    model = User
    schema = users_schema
    endpoint = "users.all-users"


class UserResource(Resource):

    @authenticated_user
    @permission_required(
        resource_model=User,
        resource_param="user_id",
        special_check=admin_or_self,
    )
    def get(self, user_id):
        """Get a user by ID"""
        user = UserService.get_by_id_or_404(user_id)
        logger.info(f"User details retrieved for user_id: {user_id}")
        return user_schema.dump(user), 200

    @authenticated_user
    @permission_required(resource_model=User)
    @validate_json_request
    @handle_errors
    def patch(self, user_id):
        """Update user details"""

        existing_user = UserService.get_by_id_or_404(user_id)
        logger.info(f"Updating user profile for user_id: {user_id}")

        updated_user = user_update_schema.load(
            get_json_data(), instance=existing_user, partial=True
        )
        db.session.commit()

        logger.info(f"User profile updated successfully for user_id: {user_id}")
        return user_schema.dump(existing_user), 200

    @authenticated_user
    @permission_required(resource_model=User)
    @handle_errors
    def delete(self, user_id):
        """Soft delete user"""

        current_user = g.current_user
        target_user = UserService.get_by_id_or_404(user_id)

        user_delete_schema.context = {
            "current_user": current_user,
        }
        user_delete_schema.load(get_json_data())
        target_user.is_deleted = True
        db.session.commit()
        delete_associated_data.delay(target_user.id)
        logger.info(f"User account soft deleted successfully: {user_id}")
        return {}, 204


class PasswordUpdateResource(Resource):
    @authenticated_user
    @permission_required(resource_model=User)
    @validate_json_request
    @handle_errors
    def post(self, user_id):
        """Update user password and invalidate old tokens"""

        target_user = UserService.get_by_id_or_404(user_id)
        password_update_schema.context = {"target_user": target_user}
        validated_data = password_update_schema.load(get_json_data())
        target_user.set_password(validated_data["new_password"])
        current_token = get_bearer_token()
        UserService.invalidate_other_tokens(target_user.id, current_token)
        db.session.commit()
        logger.info(f"Password updated successfully for user: {target_user.username}")
        return {"message": "Password has been updated successfully"}, 200


class UserEmailUpdateResource(Resource):
    """Handles email update requests with distinct workflows based on user type.
    - Regular/staff user updating own email: OTP verification workflow
    - Staff updating another user's email: Token verification workflow
    """

    @authenticated_user
    @permission_required(resource_model=User)
    @validate_json_request
    @handle_errors
    def post(self, user_id):
        """Initiate email update request with OTP verification for regular users."""

        requesting_user = g.current_user
        target_user = UserService.get_by_id_or_404(user_id)
        email_change_request_schema.context = {"user": target_user}
        validated_data = email_change_request_schema.load(get_json_data())
        new_email = validated_data["new_email"]
        if str(requesting_user.id) == str(user_id):
            EmailChangeService.request_email_change(target_user, new_email)
            return {
                "message": "We've sent one-time passwords to both your current and new email addresses. Please check both inboxes to verify your email change."
            }, 200

        token = StaffEmailChangeService.generate_staff_email_change_token(
            target_user, new_email
        )
        verification_url = url_for(
            "users.email-token-verify", token=token, _external=True
        )

        send_staff_email_verification.delay(
            new_email, verification_url, target_user.username
        )

        return {
            "message": f"We've sent a confirmation link to {new_email}. Please ask the user to check their inbox and click the link to complete the email update."
        }, 200


class EmailUpdateConfirmationResource(Resource):
    """Manages email update confirmation using OTP verification"""

    @authenticated_user
    @permission_required(resource_model=User)
    @validate_json_request
    @handle_errors
    def post(self, user_id=None):
        """Confirm email update using OTP verification"""

        target_user = UserService.get_by_id_or_404(user_id)
        validated_data = email_change_confirm_schema.load(get_json_data())
        EmailChangeService.confirm_email_change(
            target_user,
            validated_data["current_email_otp"],
            validated_data["new_email_otp"],
        )
        return {
            "message": "Great news! Your email address has been updated successfully. You can now use your new email to log in."
        }, 200


class EmailUpdateTokenVerificationResource(Resource):
    """Handles verification of staff-initiated email update tokens"""

    def get(self, token):
        if not token:
            return {
                "error": "We need a verification token to proceed. Please use the link from your email."
            }, 400

        user_id, new_email = StaffEmailChangeService.verify_staff_email_change_token(
            token
        )
        if not user_id or not new_email:
            return {
                "error": "Sorry, this verification link is either invalid or has expired. Please request a new one."
            }, 400
        user = User.query.filter(User.id == user_id, User.is_deleted == False).first()
        if not user:
            return {"error": "We couldn't find this user in our system."}, 404
        user.email = new_email
        db.session.commit()
        return {
            "message": "Success! The email address has been updated. The user can now log in with their new email."
        }, 200
