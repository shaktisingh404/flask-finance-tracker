from marshmallow.exceptions import ValidationError
from app.core.logger import logger
import redis
from flask_limiter.errors import RateLimitExceeded

from flask import jsonify


def setup_exception_handlers(application):
    """Configure exception handlers for the application."""

    @application.errorhandler(ValidationError)
    def process_validation_failure(error):
        """Process Marshmallow schema validation failures"""
        if isinstance(error.messages, dict):
            processed_errors = {
                field: messages[0] if isinstance(messages, list) else messages
                for field, messages in error.messages.items()
            }
        elif isinstance(error.messages, list):
            processed_errors = (
                error.messages[0] if len(error.messages) > 0 else "validation_failed"
            )

        logger.warning(f"Input validation failed: {processed_errors}")
        return {"error": processed_errors}, 400

    @application.errorhandler(404)
    def process_resource_missing(error):
        """Process 404 Resource Missing errors"""
        logger.info(f"Resource unavailable: {str(error)}")
        return {
            "error": "Resource Not Found",
        }, 404

    @application.errorhandler(403)
    def process_access_denied(error):
        """Process 403 Access Denied errors"""
        logger.info(f"Access restricted: {str(error)}")
        return {
            "error": "Access Denied",
        }, 403

    @application.errorhandler(401)
    def process_auth_required(error):
        """Process 401 Authentication Required errors"""
        logger.info(f"Authentication failed: {str(error)}")
        return {
            "error": "Authentication Needed",
        }, 401

    @application.errorhandler(redis.RedisError)
    def handle_redis_error(error):
        """Handle Redis connection and operational errors"""
        logger.error(f"Redis error: {str(error)}", exc_info=True)
        return {
            "error": "Service temporarily unavailable. Please try again later."
        }, 503

    @application.errorhandler(Exception)
    def process_system_error(error):
        """Process all other unexpected system errors"""
        logger.error(f"System error occurred: {str(error)}", exc_info=True)
        return {"error": str(error)}, 500
