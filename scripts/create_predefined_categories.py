# import sys
# from pathlib import Path
# from datetime import datetime

# # Add the project root directory to Python path
# project_root = str(Path(__file__).parent.parent)
# sys.path.append(project_root)

# from app import create_app
# from app.extensions import db
# from app.modules.user.models import User, UserRole
# from app.modules.category.models import Category


# def create_predefined_categories():
#     """Create predefined categories and assign them to admin user"""

#     # Create Flask app context
#     app = create_app()

#     with app.app_context():
#         # Get admin user
#         admin_user = User.query.filter_by(role=UserRole.ADMIN.value).first()

#         if not admin_user:
#             print("No admin user found! Please create an admin user first.")
#             return False

#         # Predefined categories
#         categories = [
#             {"name": "Food & Dining"},
#             {"name": "Shopping"},
#             {"name": "Transportation"},
#             {"name": "Bills & Utilities"},
#             {"name": "Entertainment"},
#             {"name": "Health & Medical"},
#             {"name": "Salary"},
#             {"name": "Investments"},
#             {"name": "Gifts"},
#             {"name": "Other Income"},
#         ]

#         try:
#             # Create categories
#             for category_data in categories:
#                 # Check if category already exists
#                 existing_category = (
#                     Category.query.filter_by(
#                         name=category_data["name"], user_id=admin_user.id
#                     ).first()
#                     or Category.query.filter_by(
#                         name=category_data["name"], is_predefined=True
#                     ).first()
#                 )

#                 if not existing_category:
#                     category = Category(
#                         name=category_data["name"],
#                         user_id=admin_user.id,
#                         is_predefined=True,
#                         created_at=datetime.utcnow(),
#                         updated_at=datetime.utcnow(),
#                     )
#                     db.session.add(category)
#                     print(f"Created category: {category_data['name']}")
#                 else:
#                     print(f"Category already exists: {category_data['name']}")

#             db.session.commit()
#             print("\nPredefined categories created successfully!")
#             return True

#         except Exception as e:
#             print(f"Error creating categories: {str(e)}")
#             db.session.rollback()
#             return False


# if __name__ == "__main__":
#     create_predefined_categories()

import sys
from pathlib import Path
from datetime import datetime

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app import create_app
from app.extensions import db
from app.modules.user.models import User, UserRole
from app.modules.category.models import Category

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def create_predefined_categories():
    """Create predefined categories and assign them to admin user"""
    created_count = 0
    skipped_count = 0

    # Create Flask app context
    app = create_app()

    with app.app_context():
        # Get admin user
        admin_user = User.query.filter_by(role=UserRole.ADMIN.value).first()

        if not admin_user:
            print(
                f"{RED}No admin user found! Please create an admin user first.{RESET}"
            )
            return False

        # Predefined categories
        categories = [
            "Food & Dining",
            "Shopping",
            "Transportation",
            "Bills & Utilities",
            "Entertainment",
            "Health & Medical",
            "Salary",
            "Investments",
            "Gifts",
            "Other Income",
        ]

        try:
            # Create categories
            for category_name in categories:
                # Validate category name
                if not category_name or len(category_name) > 50:
                    print(
                        f"{YELLOW}Skipping invalid category name: {category_name}{RESET}"
                    )
                    continue

                # Check if category already exists
                existing_category = (
                    Category.query.filter_by(
                        name=category_name, user_id=admin_user.id
                    ).first()
                    or Category.query.filter_by(
                        name=category_name, is_predefined=True
                    ).first()
                )

                if not existing_category:
                    category = Category(
                        name=category_name,
                        user_id=admin_user.id,
                        is_predefined=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.session.add(category)
                    print(f"{GREEN}Created category: {category_name}{RESET}")
                    created_count += 1
                else:
                    print(f"{YELLOW}Category already exists: {category_name}{RESET}")
                    skipped_count += 1

            db.session.commit()
            print(f"\n{GREEN}Summary:")
            print(f"✓ Categories created: {created_count}")
            print(f"⚠ Categories skipped: {skipped_count}")
            print(f"Total categories processed: {len(categories)}{RESET}")
            return True

        except Exception as e:
            print(f"{RED}Error creating categories: {str(e)}{RESET}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    create_predefined_categories()
