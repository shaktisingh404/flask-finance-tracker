from flask_restful import Resource
from flask import request, g
import uuid
from marshmallow import ValidationError
from app.extensions import db
from app.modules.category.schemas import CategorySchema, CategoryUpdateSchema
from app.modules.category.services import CategoryService
from app.modules.category.models import Category
from app.core.permissions import permission_required, admin_only
from app.core.decorators import validate_json_request, handle_errors
from app.core.authentication import authenticated_user
from app.core.responses import validation_error_response
from app.core.logger import logger
from app.core.pagination import paginate
from app.core.constants import UserRole
from app.modules.user.models import User
from app.core.utils import BaseListResource

# Initialize schemas once
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
category_update_schema = CategoryUpdateSchema()


class AllCategoryListResource(BaseListResource):
    method_decorators = [admin_only, authenticated_user]
    model = Category
    schema = categories_schema
    endpoint = "categories.all-categories"


class CategoryListResource(Resource):
    method_decorators = [
        handle_errors,
        permission_required(resource_model=Category),
        authenticated_user,
    ]

    def get(self, user_id):
        """List all categories for the authenticated user or all categories for staff."""
        current_user = g.current_user
        logger.info(f"User {current_user.id} retrieving categories")

        if current_user.role.value == UserRole.ADMIN.value:
            categories = Category.query.filter(Category.user_id == user_id).order_by(
                Category.created_at.desc()
            )
        else:
            categories = Category.query.filter(
                ((Category.user_id == user_id) & (Category.is_deleted == False))
                | ((Category.is_predefined == True) & (Category.is_deleted == False))
            ).order_by(Category.created_at.desc())
        result = paginate(
            query=categories, schema=categories_schema, endpoint="categories.categories"
        )
        return result, 200

    def post(self, user_id):
        """Create a new category for the authenticated user."""
        current_user = g.current_user
        logger.info(f"Creating new category for user {current_user.id}")
        data = request.get_json()
        data["user_id"] = user_id

        # Deserialize the data into a dictionary
        deserialized_data = category_schema.load(data)

        # Create a new Category instance using the deserialized data
        new_category = Category(**deserialized_data)

        # Handle predefined status for admin users
        target_user = User.query.get(user_id)
        if target_user and target_user.role == UserRole.ADMIN:
            new_category.is_predefined = True
        # Add to the session and commit
        db.session.add(new_category)
        db.session.commit()

        logger.info(f"Category created successfully: {new_category.id}")
        return category_schema.dump(new_category), 201


class CategoryDetailResource(Resource):
    method_decorators = [
        handle_errors,
        permission_required(resource_model=Category, resource_param="category_id"),
        authenticated_user,
    ]

    def get(self, user_id, category_id):
        """Retrieve a specific category."""
        category = Category.query.filter(
            Category.id == category_id,
            Category.is_deleted == False,
            Category.user_id == user_id,
        ).first()
        logger.info(f"Category details retrieved for category_id: {category_id}")
        return category_schema.dump(category), 200

    def patch(self, user_id, category_id):
        """Update a specific category."""
        existing_category = Category.query.get_or_404(category_id)
        logger.info(f"Updating category {category_id}")
        data = request.get_json()
        # Validate and update
        category_update_schema.load(data, instance=existing_category, partial=True)
        db.session.commit()
        logger.info(f"Category updated successfully: {category_id}")
        return category_schema.dump(existing_category), 200

    def delete(self, user_id, category_id):
        """Soft-delete a specific category."""
        category = Category.query.get_or_404(category_id)
        if not CategoryService.can_delete_category(category_id):
            raise ValidationError(
                "Cannot delete category with associated transactions, budgets or recurring transactions."
            )
        category.is_deleted = True
        db.session.commit()

        logger.info(f"Category and associated budgets soft-deleted: {category_id}")
        return {}, 204
