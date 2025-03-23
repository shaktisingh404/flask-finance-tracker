import sys
import os
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app import create_app
from app.extensions import db
from app.modules.user.models import User, UserRole
from app.extensions import bcrypt


def create_admin_user(username, email, password):
    """Create an admin user"""

    # Create Flask app context
    app = create_app()

    with app.app_context():
        # Check if admin user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists")
            return False

        # Create new admin user
        try:
            admin = User(
                username=username,
                email=email,
                password=bcrypt.generate_password_hash(password).decode("utf-8"),
                role=UserRole.ADMIN,
                is_verified=True,  # Admin user is automatically verified
            )

            db.session.add(admin)
            db.session.commit()

            print(f"Admin user created successfully!")
            print(f"Username: {username}")
            print(f"Email: {email}")
            return True

        except Exception as e:
            print(f"Error creating admin user: {str(e)}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")

    args = parser.parse_args()

    create_admin_user(args.username, args.email, args.password)
