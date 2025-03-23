from flask import Blueprint
from flask_restful import Api
from app.modules.category.resources import (
    CategoryListResource,
    CategoryDetailResource,
    AllCategoryListResource,
)
import uuid

# Create a blueprint for the users module
category_bp = Blueprint("categories", __name__)
category_api = Api(category_bp)

# Add resources to the API
category_api.add_resource(
    AllCategoryListResource, "/categories", endpoint="all-categories"
)
category_api.add_resource(
    CategoryListResource, "/<user_id>/categories", endpoint="categories"
)
category_api.add_resource(
    CategoryDetailResource, "/<user_id>/categories/<category_id>", endpoint="category"
)


# Function to initialize routes
def categories_routes(app):
    app.register_blueprint(category_bp, url_prefix="/api/users")
