import secrets
import string
from app.extensions import db, redis_client
from app.modules.user.models import User
from app.core.logger import logger
from flask import abort
from marshmallow import ValidationError
from app.modules.auth.models import ActiveAccessToken
from app.modules.user.tasks import send_email_change_otp_pair
from app.core.constants import EmailChangeConstants
from app.config import (
    OTP_VALIDITY_SECONDS,
    OTP_LENGTH,
    TOKEN_VALIDITY_SECONDS,
    RATE_LIMIT_MESSAGE,
)


class UserService:
    """Service class for User-related operations."""

    @staticmethod
    def get_by_id_or_404(user_id):
        """Get a user by ID or raise 404 if not found."""
        user = User.query.get(user_id)
        if not user or user.is_deleted:
            logger.warning(f"User not found: {user_id}")
            abort(404, description=f"User not found with ID: {user_id}")
        return user

    @staticmethod
    def invalidate_other_tokens(user_id, current_token=None):

        query = ActiveAccessToken.query.filter_by(user_id=user_id)

        if current_token:
            query = query.filter(ActiveAccessToken.token != current_token)

        tokens_to_delete = query.all()

        # Delete the tokens
        for token in tokens_to_delete:
            db.session.delete(token)

        # No need to commit here - this should be part of a larger transaction

        # Log the operation if tokens were invalidated
        if tokens_to_delete:
            logger.info(
                f"Invalidated {len(tokens_to_delete)} previous login sessions for user_id: {user_id}"
            )

        return len(tokens_to_delete)


class EmailChangeService:
    @staticmethod
    def _generate_otp(length=OTP_LENGTH):
        """Generate a random numeric OTP of specified length."""
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def _get_redis_key(user_id, prefix="email_change"):
        """Generate a Redis key for storing email change data."""
        return f"{prefix}:{user_id}"

    @staticmethod
    def request_email_change(user, new_email):
        """Request an email change with OTP verification."""
        redis_key = EmailChangeService._get_redis_key(user.id)

        # Check rate limiting
        if redis_client.exists(redis_key):
            time_remaining = redis_client.ttl(redis_key)
            minutes_remaining = int(time_remaining / 60) + 1
            raise ValidationError(RATE_LIMIT_MESSAGE.format(minutes=minutes_remaining))
        try:
            # Generate OTPs
            current_email_otp = EmailChangeService._generate_otp()
            new_email_otp = EmailChangeService._generate_otp()

            # Store in Redis
            redis_client.setex(
                redis_key,
                OTP_VALIDITY_SECONDS,
                f"{new_email}:{current_email_otp}:{new_email_otp}",
            )

            # Send OTPs asynchronously
            send_email_change_otp_pair.delay(
                user.email, new_email, current_email_otp, new_email_otp
            )

            logger.info(
                f"Email change OTPs sent for user {user.id}: {user.email} -> {new_email}"
            )
            return True

        except Exception as e:
            logger.error(f"Error requesting email change: {str(e)}", exc_info=True)
            raise Exception(f"Failed to process email change request: {str(e)}")

    @staticmethod
    def confirm_email_change(user, current_email_otp, new_email_otp):
        """Confirm email change with OTP verification."""
        redis_key = EmailChangeService._get_redis_key(user.id)
        stored_data = redis_client.get(redis_key)

        if not stored_data:
            raise ValidationError("OTP has expired")

        try:
            new_email, stored_current_otp, stored_new_otp = stored_data.split(":")

            # Validate OTPs
            if (
                current_email_otp != stored_current_otp
                and new_email_otp != stored_new_otp
            ):
                raise ValidationError("Both OTPs are incorrect")
            if current_email_otp != stored_current_otp:
                raise ValidationError("Invalid current email OTP")
            if new_email_otp != stored_new_otp:
                raise ValidationError("Invalid new email OTP")

            # Update email and clean up
            user.email = new_email
            db.session.commit()
            redis_client.delete(redis_key)

            logger.info(f"Email changed for user {user.id} to {new_email}")
            return True

        except ValidationError as e:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error confirming email change: {str(e)}", exc_info=True)
            raise Exception(f"Failed to change email: {str(e)}")


class StaffEmailChangeService:
    @staticmethod
    def generate_staff_email_change_token(user, new_email):
        """Generate a token for staff-initiated email change."""
        token = secrets.token_urlsafe(32)
        redis_key = EmailChangeService._get_redis_key(token, "staff_email_change")

        try:
            redis_client.setex(
                redis_key,
                TOKEN_VALIDITY_SECONDS,
                f"{user.id}:{new_email}",
            )
            logger.info(
                f"Staff email change token generated for user {user.id}: {user.email} -> {new_email}"
            )
            return token
        except Exception as e:
            logger.error(
                f"Error generating staff email change token: {str(e)}", exc_info=True
            )
            raise Exception(f"Failed to generate email change token: {str(e)}")

    @staticmethod
    def verify_staff_email_change_token(token):
        """Verify and consume a staff email change token."""
        redis_key = EmailChangeService._get_redis_key(token, "staff_email_change")
        stored_data = redis_client.get(redis_key)
        if not stored_data:
            return None, None
        redis_client.delete(redis_key)
        user_id, new_email = stored_data.split(":")
        return user_id, new_email
