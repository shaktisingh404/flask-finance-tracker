import os
import secrets
from datetime import datetime, timedelta
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
from itsdangerous import URLSafeTimedSerializer
from app.modules.auth.models import ActiveAccessToken
from app.extensions import db, redis_client
from app.core.logger import logger
from app.config import (
    JWT_ACCESS_TOKEN_EXPIRES,
    JWT_REFRESH_TOKEN_EXPIRES,
    REDIS_VALID_TTL,
    REDIS_RATE_LIMIT_TTL,
)


class TokenUtils:
    """Utility class to handle all token-related operations."""

    @staticmethod
    def generate_access_token(user, fresh=True):
        """Generate an access token with freshness option."""
        expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRES)
        additional_claims = {
            "role": user.role.value if hasattr(user.role, "value") else str(user.role)
        }
        token = create_access_token(
            identity=str(user.id),
            fresh=fresh,
            expires_delta=expires_delta,
            additional_claims=additional_claims,
        )
        token_entry = ActiveAccessToken(token=token, user_id=user.id)
        db.session.add(token_entry)
        db.session.commit()
        logger.info(f"Generated access token for user_id: {user.id}")
        return token

    @staticmethod
    def generate_refresh_token(user):
        """Generate a refresh token for a user."""
        expires_delta = timedelta(days=JWT_REFRESH_TOKEN_EXPIRES)
        token = create_refresh_token(identity=str(user.id), expires_delta=expires_delta)
        logger.info(f"Generated refresh token for user_id: {user.id}")
        return token

    @staticmethod
    def invalidate_access_token(token):
        """
        Invalidate a specific access token.
        """
        token_entry = ActiveAccessToken.query.filter_by(token=token).first()
        if token_entry:
            db.session.delete(token_entry)
            db.session.commit()
            logger.info(
                f"Logout successfully and Invalidated token for user: {token_entry.user.username}"
            )

    @staticmethod
    def invalidate_user_access_tokens(user_id):
        """Invalidate all active access tokens for a given user."""
        tokens = ActiveAccessToken.query.filter_by(user_id=user_id).all()
        if tokens:
            for token in tokens:
                db.session.delete(token)
            db.session.commit()
            logger.info(f"Invalidated all access tokens for user_id: {user_id}")
            return True
        logger.info(f"No active tokens found to invalidate for user_id: {user_id}")
        return False

    # Password Reset Token Methods
    @staticmethod
    def generate_password_reset_token():
        """Generate a secure random token for password reset."""
        token = secrets.token_urlsafe(32)
        logger.info("Generated password reset token")
        return token

    @staticmethod
    def store_reset_token(user_id, token):
        """Store a password reset token in Redis with expiration."""
        key = f"password_reset:{token}"
        rate_limit_key = f"reset_rate_limit:{user_id}"
        valid_ttl = REDIS_VALID_TTL  # Default 15 minutes (900 seconds)
        rate_limit_ttl = REDIS_RATE_LIMIT_TTL  # Default 10 minutes (600 seconds)

        try:
            redis_client.setex(key, valid_ttl, str(user_id))

            if not redis_client.exists(rate_limit_key):
                redis_client.setex(rate_limit_key, rate_limit_ttl, "1")
            logger.info(f"Stored reset token for user_id: {user_id}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to store reset token for user_id: {user_id}: {str(e)}"
            )
            return False

    @staticmethod
    def verify_reset_token(token):
        """Verify a password reset token and return the associated user ID."""
        key = f"password_reset:{token}"
        try:
            user_id = redis_client.get(key)
            if user_id:
                redis_client.delete(key)
                logger.info(f"Verified and deleted reset token for user_id: {user_id}")
                return (
                    user_id.decode("utf-8") if isinstance(user_id, bytes) else user_id
                )
            logger.warning(f"Invalid or expired reset token: {token[:10]}...")
            return None
        except Exception as e:
            logger.error(f"Error verifying reset token: {str(e)}")
            return None
