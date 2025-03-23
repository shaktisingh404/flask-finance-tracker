from functools import wraps
from flask import g, jsonify, request
from app.core.constants import UserRole
from app.modules.user.models import User, UserRelationship
from app.modules.category.models import Category


def admin_only(f):
    """Decorator to allow only admin users to access an endpoint"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, "current_user") or not g.current_user:
            return {"error": "Authentication required"}, 401

        if g.current_user.role != UserRole.ADMIN:
            return {"error": "Admin privileges required"}, 403

        return f(*args, **kwargs)

    return decorated_function


def admin_or_self(current_user, target_user_id, kwargs, request):
    """
    Special check function for permission_required decorator.
    Allows access only if:
    1. The current user is accessing their own resources OR
    2. The current user is an admin

    Returns error response if access should be denied, None otherwise
    """
    # Allow if user is admin
    if current_user.role == UserRole.ADMIN:
        return None

    # Allow if user is accessing their own resources
    if str(current_user.id) == str(target_user_id):
        return None

    # Deny access in all other cases
    return {"error": "Resource not found"}, 404


def prevent_child_creation(model_name):
    """
    Decorator to prevent:
    1. Child users from creating resources
    2. Child users cannot have child of their own
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            # Child users can't create any resources
            if g.current_user.role == UserRole.CHILD_USER:
                return {"error": f"Child cannot create {model_name} resources"}, 403

            # For user creation endpoint
            if model_name == "user":
                parent_id = kwargs.get("user_id")

                if parent_id:
                    parent_user = User.query.get(parent_id)
                    if not parent_user:
                        return {"error": "Parent user not found"}, 404

                    # Admin can't create child user for themselves
                    if g.current_user.role == UserRole.ADMIN and str(
                        g.current_user.id
                    ) == str(parent_id):
                        return {
                            "error": "Admin cannot create child user for themselves"
                        }, 403

                    # Child users can't have child
                    if parent_user.role == UserRole.CHILD_USER:
                        return {
                            "error": "Child users cannot have child of their own"
                        }, 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def permission_required(
    resource_model=None,
    resource_param=None,
    allow_parent_write=False,
    special_check=None,
):
    """
    A flexible permission decorator that works with the hierarchical URL structure:
    /api/users/<user_id>/resource_type/<resource_id>

    Args:
        resource_model: Database model for the resource (Category, Transaction, etc.)
        resource_param: URL parameter name for resource ID (category_id, transaction_id, etc.)
        allow_parent_write: Whether parent users can modify child's resources
        special_check: A function that performs additional access checks
                      (e.g., restricting profile access to only the user themselves)
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check authentication

            # Get target user_id from URL parameters
            target_user_id = kwargs.get("user_id")
            if not target_user_id:
                return {"error": "User ID is required"}, 400

            # Run special access check if provided
            if special_check:
                special_check_result = special_check(
                    g.current_user, target_user_id, kwargs, request
                )
                if special_check_result:
                    return special_check_result

            # Special handling for predefined categories - allow read access to any user
            if (
                resource_model
                and resource_model == Category
                and resource_param in kwargs
            ):
                category_id = kwargs.get(resource_param)
                print(category_id)
                if category_id:
                    category = Category.query.filter_by(
                        id=category_id, user_id=kwargs.get("user_id")
                    ).first()
                    print(category)
                    if (
                        category
                        and hasattr(category, "is_predefined")
                        and category.is_predefined
                    ):
                        # Allow read access to predefined categories
                        if request.method == "GET":
                            return f(*args, **kwargs)
                        # Only admins can modify predefined categories
                        elif g.current_user.role != UserRole.ADMIN:
                            return {"error": "Cannot modify predefined categories"}, 403

            # Get target user_id from URL parameters
            target_user_id = kwargs.get("user_id")
            if not target_user_id:
                return {"error": "User ID is required"}, 400

            # Get target user
            target_user = User.query.get(target_user_id)
            if not target_user:
                return {"error": "User not found"}, 404

            # Determine request type
            method = request.method
            is_read_operation = method == "GET"
            is_write_operation = method in ["POST", "PUT", "PATCH", "DELETE"]

            # Access control logic based on user relationships
            can_access = False

            # Admin can access any user's resources
            if g.current_user.role == UserRole.ADMIN:
                can_access = True
            # User can access their own resources
            elif str(g.current_user.id) == str(target_user_id):
                can_access = True
            # Parent-child relationship check
            else:
                # Check if current user is parent of target user
                relationship = UserRelationship.query.filter_by(
                    parent_id=g.current_user.id,
                    child_id=target_user_id,
                    is_deleted=False,
                ).first()

                if relationship:
                    # Parent can always read child resources
                    if is_read_operation:
                        can_access = True
                    # Parents can write child resources only if explicitly allowed
                    elif is_write_operation and allow_parent_write:
                        can_access = True

            # If access denied, return appropriate error
            if not can_access:
                if relationship and is_write_operation and not allow_parent_write:
                    return {
                        "error": "Parents can view but not modify their child's resources"
                    }, 403
                else:
                    return {"error": "Resource Not Found"}, 404

            if resource_model and resource_param and resource_param in kwargs:
                resource_id = kwargs.get(resource_param)
                if not resource_id:
                    return {"error": f"Resource ID ({resource_param}) is required"}, 400

                # Get the specific resource and check if it's not soft-deleted
                resource = resource_model.query.get(resource_id)
                if not resource or (
                    hasattr(resource, "is_deleted") and resource.is_deleted
                ):
                    return {
                        "error": f"{resource_param.replace('_id', '').title()} not found"
                    }, 404

                # Check if resource belongs to target user
                # Skip this check for predefined categories
                is_predefined_category = (
                    resource_model == Category
                    and hasattr(resource, "is_predefined")
                    and resource.is_predefined
                )

                if (
                    hasattr(resource, "user_id")
                    and str(resource.user_id) != str(target_user_id)
                    and not is_predefined_category
                ):
                    resource_type = resource_model.__name__.lower()
                    return {
                        "error": f"This {resource_type} does not belong to the specified user"
                    }, 403

                # Special handling for predefined items
                if hasattr(resource, "is_predefined") and resource.is_predefined:
                    if g.current_user.role != UserRole.ADMIN and is_write_operation:
                        return {"error": "Cannot modify predefined items"}, 403

            # All checks passed, proceed to the handler
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# from functools import wraps
# from flask import g, jsonify, request
# from app.core.constants import UserRole
# from app.modules.user.models import User, UserRelationship
# from app.modules.category.models import Category


# def admin_only(f):
#     """Decorator to allow only admin users to access an endpoint"""

#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if not hasattr(g, "current_user") or not g.current_user:
#             return {"error": "Authentication required"}, 401
#         if g.current_user.role != UserRole.ADMIN:
#             return {"error": "Admin privileges required"}, 403
#         return f(*args, **kwargs)

#     return decorated_function


# def admin_or_self(current_user, target_user_id, kwargs, request):
#     """
#     Special check function for permission_required decorator.
#     """
#     if current_user.role == UserRole.ADMIN:
#         return None
#     if str(current_user.id) == str(target_user_id):
#         return None
#     return {"error": "Resource not found"}, 404


# def prevent_child_creation(model_name):
#     """Decorator to prevent child users from creating resources"""

#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             if g.current_user.role == UserRole.CHILD_USER:
#                 return {"error": f"Child cannot create {model_name} resources"}, 403

#             if model_name == "user":
#                 parent_id = kwargs.get("user_id")
#                 if parent_id:
#                     parent_user = User.query.get(parent_id)
#                     if not parent_user:
#                         return {"error": "Parent user not found"}, 404
#                     if g.current_user.role == UserRole.ADMIN and str(
#                         g.current_user.id
#                     ) == str(parent_id):
#                         return {
#                             "error": "Admin cannot create child user for themselves"
#                         }, 403
#                     if parent_user.role == UserRole.CHILD_USER:
#                         return {
#                             "error": "Child users cannot have child of their own"
#                         }, 403
#             return f(*args, **kwargs)

#         return decorated_function

#     return decorator


# def check_category_permissions(resource_model, resource_param, kwargs):
#     """Separate method to handle category-specific permissions"""
#     if resource_model != Category or resource_param not in kwargs:
#         return None

#     category_id = kwargs.get(resource_param)
#     user_id = kwargs.get("user_id")

#     if category_id:
#         category = Category.query.filter_by(id=category_id, user_id=user_id).first()
#         if not category:
#             return {"error": "Category not found"}, 404

#         if category.is_predefined:
#             if request.method == "GET":
#                 return None
#             if g.current_user.role != UserRole.ADMIN:
#                 return {"error": "Cannot modify predefined categories"}, 403
#     return None


# def permission_required(
#     resource_model=None,
#     resource_param=None,
#     allow_parent_write=False,
#     special_check=None,
# ):
#     """Permission decorator with category logic in separate method"""

#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             target_user_id = kwargs.get("user_id")
#             if not target_user_id:
#                 return {"error": "User ID is required"}, 400

#             if special_check:
#                 special_check_result = special_check(
#                     g.current_user, target_user_id, kwargs, request
#                 )
#                 if special_check_result:
#                     return special_check_result

#             # Check category-specific permissions
#             category_result = check_category_permissions(
#                 resource_model, resource_param, kwargs
#             )
#             if category_result:
#                 return category_result

#             target_user = User.query.get(UUID(target_user_id))
#             if not target_user:
#                 return {"error": "User not found"}, 404

#             method = request.method
#             is_read_operation = method == "GET"
#             is_write_operation = method in ["POST", "PUT", "PATCH", "DELETE"]

#             can_access = False
#             if g.current_user.role == UserRole.ADMIN:
#                 can_access = True
#             elif str(g.current_user.id) == str(target_user_id):
#                 can_access = True
#             else:
#                 relationship = UserRelationship.query.filter_by(
#                     parent_id=g.current_user.id,
#                     child_id=target_user_id,
#                     is_deleted=False,
#                 ).first()
#                 if relationship:
#                     if is_read_operation:
#                         can_access = True
#                     elif is_write_operation and allow_parent_write:
#                         can_access = True

#             if not can_access:
#                 if relationship and is_write_operation and not allow_parent_write:
#                     return {
#                         "error": "Parents can view but not modify their child's resources"
#                     }, 403
#                 return {"error": "Access denied to this user's resources"}, 403

#             if resource_model and resource_param and resource_param in kwargs:
#                 resource_id = kwargs.get(resource_param)
#                 if not resource_id:
#                     return {"error": f"Resource ID ({resource_param}) is required"}, 400

#                 resource = resource_model.query.get(resource_id)
#                 if not resource or (
#                     hasattr(resource, "is_deleted") and resource.is_deleted
#                 ):
#                     return {
#                         "error": f"{resource_param.replace('_id', '').title()} not found"
#                     }, 404

#                 if (
#                     hasattr(resource, "user_id")
#                     and str(resource.user_id) != str(target_user_id)
#                     and not (
#                         resource_model == Category
#                         and hasattr(resource, "is_predefined")
#                         and resource.is_predefined
#                     )
#                 ):
#                     resource_type = resource_model.__name__.lower()
#                     return {
#                         "error": f"This {resource_type} does not belong to the specified user"
#                     }, 403

#             return f(*args, **kwargs)

#         return decorated_function

#     return decorator
