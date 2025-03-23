# app/modules/auth/urls.py
from flask import Blueprint
from app.extensions import api
from flask_restful import Api
from app.modules.auth.resources import (
    SignupResource,
    LoginResource,
    LogoutResource,
    VerifyEmailResource,
    PasswordResetRequestResource,
    PasswordResetConfirmResource,
    ChildUserResource,
    RegisterAdminResource,
)

# Create a blueprint for auth routes
auth_bp = Blueprint("auth", __name__)

# Create an API instance tied to the Blueprint
auth_api = Api(auth_bp)  # Instead of using the global `api`

# Add resources to the new API instance
auth_api.add_resource(SignupResource, "/auth/signup", endpoint="auth_signup")
auth_api.add_resource(LoginResource, "/auth/login", endpoint="auth_login")
auth_api.add_resource(LogoutResource, "/auth/logout", endpoint="auth_logout")
auth_api.add_resource(
    PasswordResetRequestResource,
    "/auth/reset-password-request",
    endpoint="auth-reset-password",
)
auth_api.add_resource(
    RegisterAdminResource, "/auth/register-admin", endpoint="register-admin"
)
auth_api.add_resource(
    PasswordResetConfirmResource,
    "/auth/reset-password-confirm/<token>",
    endpoint="auth-reset-password-confirm",
)
auth_api.add_resource(
    VerifyEmailResource, "/auth/verify-user/<token>", endpoint="verify-user"
)

# Add the child user resource
auth_api.add_resource(
    ChildUserResource,
    "/users/<user_id>/child",
    endpoint="create-child-user",
)


def register_auth_routes(app):
    """Register authentication routes with the app."""
    app.register_blueprint(auth_bp, url_prefix="/api")
