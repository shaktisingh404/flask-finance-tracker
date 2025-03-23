from flask import Blueprint
from flask_restful import Api
from app.modules.user.resources import (
    UserListResource,
    UserResource,
    PasswordUpdateResource,
    UserEmailUpdateResource,
    EmailUpdateConfirmationResource,
    EmailUpdateTokenVerificationResource,
)
from app.modules.auth.resources import ChildUserResource

# Create a blueprint for the users module
users_bp = Blueprint("users", __name__)
users_api = Api(users_bp)


# Add resources to the API
users_api.add_resource(UserListResource, "/", endpoint="all-users")
users_api.add_resource(
    UserResource,
    "/<user_id>",
    endpoint="user",
)
users_api.add_resource(
    PasswordUpdateResource,
    "/<user_id>/update-password",
    endpoint="update-password",
)


users_api.add_resource(
    UserEmailUpdateResource, "/<user_id>/update-email", endpoint="user-email-update"
)

users_api.add_resource(
    EmailUpdateConfirmationResource,
    "/<user_id>/update-email/confirm",
    endpoint="user-email-confirm",
)
# Add the child user resource
# users_bp.add_resource(
#     ChildUserResource,
#     "/<user_id>/child",
#     endpoint="create-child-user",
# )
users_api.add_resource(
    EmailUpdateTokenVerificationResource,
    "/verify-email/<token>",
    endpoint="email-token-verify",
)


# Function to initialize routes
def users_routes(app):
    app.register_blueprint(users_bp, url_prefix="/api/users")
