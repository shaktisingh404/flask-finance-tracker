from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from app.core.logger import logger
import redis
import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
api = Api()
ma = Marshmallow()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()
try:
    redis_client = redis.StrictRedis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
        socket_timeout=5,  # Add timeout
        socket_connect_timeout=5,  # Add connect timeout
        retry_on_timeout=True,  # Auto retry on timeout
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis connection established successfully")
except redis.RedisError as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    # Set redis_client to None so other code can check if it's available
    redis_client = None
    logger.warning("Application will run with reduced functionality")

# Create the limiter instance without initializing it
limiter = Limiter(
    key_func=get_remote_address,
    strategy=os.getenv("LIMITER_STRATEGY", "moving-window"),
    default_limits=os.getenv("LIMITER_DEFAULT_LIMITS", "10 per minute").split(","),
    storage_uri="memory://",
)


def init_limiter(app):
    """Initialize the limiter with the Flask app"""
    # Update storage configuration based on Redis availability
    if redis_client is not None:
        limiter.storage_uri = "redis://"
        limiter.storage_options = {"redis": redis_client}
        logger.info("Rate limiter using Redis storage")
    else:
        logger.warning("Rate limiter using in-memory storage")
    # Initialize with app
    limiter.init_app(app)
    # This is crucial - make sure Flask-Limiter uses your app's handlers
    app.config.setdefault("RATELIMIT_HEADERS_ENABLED", True)
    app.config.setdefault("RATELIMIT_IN_MEMORY_FALLBACK_ENABLED", True)
    app.config.setdefault("RATELIMIT_USE_FLASK_EXCEPTION_HANDLER", True)
    logger.info(f"Flask-Limiter initialized with strategy:  limits: ")
