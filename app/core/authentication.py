from functools import wraps
from flask import request, g
from flask_jwt_extended import jwt_required, get_jwt
from app.extensions import db
from app.modules.auth.models import ActiveAccessToken
from .logger import logger


def authenticated_user(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ")[1]
        token_record = ActiveAccessToken.query.filter_by(token=token).first()

        if not token_record:
            logger.warning(f"Invalid or revoked token: {token[:10]}...")
            return {"error": "Invalid or revoked token!"}, 401

        user = token_record.user
        if not user:
            logger.warning(f"User not found")
            return {"error": "User not found!"}, 401
        claims = get_jwt()
        role_value = claims.get("role")
        g.role = role_value
        g.current_user = user
        logger.info(f"Request authenticated for user: {user.username}")
        return f(*args, **kwargs)

    return decorated
