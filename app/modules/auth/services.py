from app.core.tokens import TokenUtils
from app.config import REDIS_VALID_TTL, REDIS_RATE_LIMIT_TTL
from app.core.constants import UserRole
from app.modules.user.models import User
from app.extensions import db, redis_client
from app.core.logger import logger
from marshmallow.exceptions import ValidationError
import uuid
from flask import url_for
from app.modules.auth.tasks import send_password_reset_email, send_verification_email
from app.modules.user.models import UserRelationship
import json
from app.modules.user.schemas import UserSchema


class RegistrationService:
    """Handle user registration with Redis-based pending verification"""

    @staticmethod
    def get_redis_serializable_dict(user_instance):
        """Convert a User instance to a Redis-serializable dictionary"""
        # First dump to dict with marshmallow
        user_schema = UserSchema()
        data = user_schema.dump(user_instance)
        # Handle any special fields like enums
        if hasattr(user_instance.role, "value"):
            data["role"] = user_instance.role.value

        if hasattr(user_instance.gender, "value"):
            data["gender"] = user_instance.gender.value

        # Add password since it's load_only and won't be in dumped data
        data["password"] = user_instance.password
        return data

    @staticmethod
    def initiate_registration(user_data, parent_id=None):
        """
        Store registration data in Redis and send verification

        Args:
            user_data: User data object to register
            parent_id: Optional parent UUID if this is a child user

        Returns:
            token: Verification token
        """
        # Check if email is pending verification
        pending_email_key = RedisHelper.pending_email_key(user_data.email)
        if redis_client.exists(pending_email_key) > 0:
            ttl = redis_client.ttl(pending_email_key)
            minutes = int(ttl / 60) + 1
            raise ValidationError(
                f"This email is awaiting verification. Please wait {minutes} minutes before trying again"
            )
        # Generate verification token
        token = str(uuid.uuid4())

        # Prepare user data for Redis - handle all potential serialization issues
        serialized_data = RegistrationService.get_redis_serializable_dict(user_data)

        # If this is a child user, store parent ID
        if parent_id:
            serialized_data["parent_id"] = str(parent_id)

        # Store data in Redis with expiration
        pending_user_key = RedisHelper.pending_user_key(token)
        redis_client.setex(
            pending_user_key, REDIS_VALID_TTL, json.dumps(serialized_data)
        )

        redis_client.setex(pending_email_key, REDIS_VALID_TTL, token)
        verification_token_key = RedisHelper.verification_token_key(token)
        redis_client.setex(verification_token_key, REDIS_VALID_TTL, user_data.email)

        # Send verification email
        verify_url = url_for("auth.verify-user", token=token, _external=True)
        send_verification_email.delay(user_data.email, verify_url)

        registration_type = "child user" if parent_id else "user"
        logger.info(
            f"{registration_type.capitalize()} registration pending verification: {user_data.email}"
        )
        return token

    @staticmethod
    def complete_registration(token):
        """Verify token and move user from Redis to database"""
        # Get verification data
        verification_token_key = RedisHelper.verification_token_key(token)
        email = redis_client.get(verification_token_key)

        if not email:
            logger.warning(f"Invalid or expired verification token: {token}")
            raise ValidationError("Invalid or expired verification token")

        # Get pending user data
        pending_user_key = RedisHelper.pending_user_key(token)
        user_data_str = redis_client.get(pending_user_key)
        user_data_dict = json.loads(user_data_str)

        # Create actual user in database
        new_user = User(
            username=user_data_dict["username"],
            email=user_data_dict["email"],
            name=user_data_dict["name"],
            role=UserRole(user_data_dict["role"]),
            is_verified=True,
            date_of_birth=user_data_dict["date_of_birth"],
            gender=user_data_dict["gender"],
        )
        new_user.set_password(user_data_dict["password"])

        try:
            db.session.add(new_user)
            db.session.flush()  # Get user ID without committing

            # Check if this is a child user that needs a parent relationship
            if "parent_id" in user_data_dict:
                parent_id = uuid.UUID(user_data_dict["parent_id"])
                relationship = UserRelationship(
                    parent_id=parent_id, child_id=new_user.id
                )
                db.session.add(relationship)
                logger.info(
                    f"Parent-child relationship created for user: {new_user.email}"
                )

            db.session.commit()

            # Clean up Redis keys
            redis_client.delete(verification_token_key)
            redis_client.delete(pending_user_key)
            redis_client.delete(RedisHelper.pending_email_key(email))

            logger.info(f"User registration completed: {new_user.email}")
            return {"username": new_user.username, "email": new_user.email}

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            raise ValidationError("Failed to complete registration")


class RedisHelper:
    """Helper class for Redis operations"""

    # In app/modules/auth/services.py - RedisHelper class
    @staticmethod
    def pending_user_key(token):
        key = f"pending_user:{token}"
        logger.debug(f"Generated pending_user_key: {key}")
        return key

    @staticmethod
    def verification_token_key(token):
        key = f"verification_token:{token}"
        logger.debug(f"Generated verification_token_key: {key}")
        return key

    @staticmethod
    def pending_email_key(email):
        return f"pending_email:{email}"

    @staticmethod
    def rate_limit_key(user_id, action_type):
        return f"{action_type}_rate_limit:{user_id}"

    @staticmethod
    def check_rate_limit(key, action_name):
        """Check if rate limited, raise exception if so"""
        if redis_client.exists(key):
            ttl = redis_client.ttl(key)
            minutes = int(ttl / 60) + 1
            logger.warning(
                f"Rate limit hit for {action_name} - must wait {minutes} minutes"
            )
            raise ValidationError(f"Please wait {minutes} minutes before trying again")


class AuthTokenService:
    """Token generation and validation"""

    @staticmethod
    def generate_tokens(user):
        """Generate access and refresh tokens for a user"""
        access_token = TokenUtils.generate_access_token(user)
        refresh_token = TokenUtils.generate_refresh_token(user)
        tokens = {"access_token": access_token, "refresh_token": refresh_token}
        logger.debug(f"Generated authentication tokens for user: {user.username}")
        return tokens

    @staticmethod
    def authenticate_user(username, password):
        """Authenticate a user with username and password"""
        user = User.query.filter_by(username=username, is_deleted=False).first()

        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            raise ValidationError("Invalid username or password")

        if not user.is_verified:
            logger.warning(f"Login attempt with unverified account: {username}")
            raise ValidationError("Please verify your email before logging in")

        if not user.check_password(password):
            logger.warning(
                f"Failed login attempt (invalid password) for user: {username}"
            )
            raise ValidationError("Invalid username or password")

        logger.info(f"User authenticated successfully: {username}")
        return user


class PasswordService:
    """Password reset and management"""

    @staticmethod
    def request_password_reset(email, endpoint="auth.auth-reset-password-confirm"):
        """Send a password reset link to user's email"""
        user = User.query.filter_by(email=email, is_deleted=False).first()
        rate_limit_key = RedisHelper.rate_limit_key(user.id, "reset")
        RedisHelper.check_rate_limit(rate_limit_key, f"password reset email to {email}")

        # Generate reset token
        token = TokenUtils.generate_password_reset_token()
        TokenUtils.store_reset_token(user.id, token)
        # Generate reset URL
        reset_url = url_for(endpoint, token=token, _external=True)

        # Send the email (asynchronous)
        send_password_reset_email.delay(email, reset_url)

        # Set rate limit for this user
        redis_client.setex(rate_limit_key, REDIS_RATE_LIMIT_TTL, "1")

        logger.info(f"Password reset email queued for: {email}")
        return True

    @staticmethod
    def reset_password_with_token(token, new_password):
        """Reset a user's password using a valid reset token"""
        user_id = TokenUtils.verify_reset_token(token)
        if not user_id:
            logger.warning(f"Invalid or expired password reset token used")
            raise ValidationError("Invalid or expired reset token")

        user = User.query.get(uuid.UUID(user_id))
        if not user or user.is_deleted:
            logger.warning(f"User not found for reset token: {token}")
            raise ValidationError("User not found")

        try:
            user.set_password(new_password)
            db.session.commit()
            TokenUtils.invalidate_user_access_tokens(user.id)
            logger.info(f"Password reset successful for user: {user.email}")
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting password: {str(e)}", exc_info=True)
            raise ValidationError("An error occurred while resetting your password")
