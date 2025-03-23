from functools import wraps
from flask import request
from marshmallow import ValidationError
from app.core.responses import validation_error_response
from app.core.logger import logger
from app.extensions import db
from app.core.responses import validation_error_response


from functools import wraps
import json
from flask import request  # Assuming Flask; adjust for your framework if different
import logging

logger = logging.getLogger(__name__)


def validate_json_request(f):
    """Decorator to validate JSON content type and ensure body is valid JSON."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ["POST", "PUT", "PATCH"]:
            # Check Content-Type header
            if request.content_type != "application/json":
                return {
                    "error": "Request must be in JSON format. Please set the Content-Type header to application/json."
                }, 415

            # Check if body is valid JSON
            try:
                if request.data:  # Only attempt parsing if there's a body
                    request.json  # This triggers parsing; adjust based on your framework
                # If no body is sent (empty), you might allow it depending on your API
                # Else, you could enforce a non-empty body with another check
            except json.JSONDecodeError:
                return {
                    "error": "Invalid JSON in request body. Please provide a valid JSON payload."
                }, 400
            except Exception as e:
                logger.error(f"Error parsing request body: {str(e)}", exc_info=True)
                return {"error": "Failed to process request body."}, 400

        # Proceed to the decorated function
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            return {
                "error": "An unexpected error occurred. Our team has been notified."
            }, 500

    return decorated


def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as err:
            return validation_error_response(err)
        except Exception as e:
            db.session.rollback()
            return {"message": f"An error occurred: {str(e)}"}, 500

    return wrapper
