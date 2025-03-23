from flask import g, request
from flask_restful import Resource
from app.modules.user.schemas import UserSchema
from app.modules.auth.schemas import (
    UserLoginSchema,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    ResendVerificationSchema,
)
import uuid
from app.modules.auth.services import (
    AuthTokenService,
    PasswordService,
    RegistrationService,
)

from app.core.authentication import authenticated_user
from app.core.responses import validation_error_response
from marshmallow import ValidationError
from app.core.tokens import TokenUtils
from app.core.logger import logger
from app.core.decorators import validate_json_request
from app.modules.user.models import User, UserRole
from app.core.permissions import prevent_child_creation, permission_required, admin_only
from app.core.decorators import handle_errors

# Schema instances
signup_schema = UserSchema()
login_schema = UserLoginSchema()
password_reset_request_schema = PasswordResetRequestSchema()
password_reset_confirm_schema = PasswordResetConfirmSchema()
resend_verification_schema = ResendVerificationSchema()
child_user_schema = UserSchema()


class RegisterAdminResource(Resource):
    @authenticated_user
    @admin_only
    @validate_json_request
    @handle_errors
    def post(self):
        """Register a new admin user."""
        logger.info("Starting admin registration process")
        raw_data = request.get_json()
        user_data = signup_schema.load(raw_data)
        user_data.role = UserRole.ADMIN
        token = RegistrationService.initiate_registration(user_data)
        logger.info("Admin registration completed successfully")
        return {
            "token": token,
            "message": "Admin registration initiated, please check your email for verification",
        }, 200


class SignupResource(Resource):
    @validate_json_request
    @handle_errors
    def post(self):
        """Register a new user."""
        logger.info("Starting user registration process")

        raw_data = request.get_json()
        user_data = signup_schema.load(raw_data)
        if not user_data.role:
            user_data.role = UserRole.USER

        token = RegistrationService.initiate_registration(user_data)
        logger.info("User registration completed successfully")
        return {
            "token": token,
            "message": "Registration initiated, please check your email for verification",
        }, 200


class LoginResource(Resource):
    @validate_json_request
    @handle_errors
    def post(self):
        """Authenticate a user and issue a token."""
        data = login_schema.load(request.get_json())
        user = AuthTokenService.authenticate_user(data["username"], data["password"])
        tokens = AuthTokenService.generate_tokens(user)
        return {
            "tokens": tokens,
        }, 200


class LogoutResource(Resource):
    @authenticated_user
    def post(self):
        """Revoke the current user's token."""
        logger.info("Received logout request")
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {
                "error": "Invalid authorization header. Please provide a valid Bearer token."
            }, 401
        token = auth_header.split(" ")[1]
        TokenUtils.invalidate_access_token(token)
        return {
            "message": "You have been successfully logged out. Thank you for using our service.",
        }, 200


class PasswordResetRequestResource(Resource):
    """Resource for requesting a password reset link"""

    @validate_json_request
    @handle_errors
    def post(self):
        logger.info("Received password reset request")
        data = password_reset_request_schema.load(request.get_json())
        PasswordService.request_password_reset(data["email"])
        return {
            "message": "Password reset instructions have been sent to your email address. Please check your inbox and follow the provided link.",
        }, 200


class PasswordResetConfirmResource(Resource):
    """Resource for confirming a password reset with token from URL"""

    @validate_json_request
    @handle_errors
    def post(self, token):
        logger.info(f"Received password reset confirmation with token: {token}")
        if not token:
            return {
                "error": "Token is missing. Please use the complete password reset link from your email."
            }, 400

        data = password_reset_confirm_schema.load(request.get_json())
        user = PasswordService.reset_password_with_token(token, data["password"])
        return {
            "message": "Your password has been successfully updated. You can now log in with your new password."
        }, 200


class VerifyEmailResource(Resource):
    @handle_errors
    def get(self, token):
        user = RegistrationService.complete_registration(token)
        return {
            "message": "Account verified successfully",
        }, 200


class ChildUserResource(Resource):
    @authenticated_user
    @permission_required(resource_model=User, allow_parent_write=False)
    def get(self, user_id):
        """Get child user details"""
        parent_user = User.query.get(user_id)
        child_user = parent_user.get_child()
        if not child_user:
            return {"error": "Child user not found"}, 404
        return {"user": UserSchema(exclude=("password",)).dump(child_user)}, 200

    @authenticated_user
    @permission_required(resource_model=User, allow_parent_write=True)
    @prevent_child_creation("user")
    def post(self, user_id):
        """Create a child user under the specified parent"""
        logger.info(f"Starting child user creation for parent ID: {user_id}")

        parent_user = User.query.get(user_id)
        if parent_user.get_child():
            return {"error": "Parent already has a child user"}, 400

        user_data = child_user_schema.load(request.get_json())
        user_data.role = UserRole.CHILD_USER
        token = RegistrationService.initiate_registration(user_data, user_id)

        logger.info("Child user creation completed successfully")
        return {
            "message": "Child user created successfully",
            "token": token,
        }, 200
