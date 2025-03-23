from flask import Flask, request, jsonify
from marshmallow.exceptions import ValidationError
from uuid import UUID
from app.extensions import db, migrate, bcrypt, jwt, mail, api, ma, init_limiter
from app.celery_app import make_celery
from app.core.logger import logger
from app.core.exceptions import setup_exception_handlers
from flask_cors import CORS
from flasgger import Swagger


def create_app(config_class="app.config.Config"):
    """Factory function to create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    if isinstance(config_class, dict):
        # Handle dictionary config (e.g., from tests)
        app.config.update(config_class)
    else:
        # Handle module/object config (e.g., app.config.Config)
        app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    api.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    init_limiter(app)
    swagger = Swagger(app)
    CORS(app)

    # Configure logger
    app.logger = logger

    # Initialize Celery
    app.celery = make_celery(app)

    # Register blueprints/routes
    register_blueprints(app)

    # Register error handlers
    setup_exception_handlers(app)

    # Apply middleware globally
    @app.before_request
    def validate_uuids():
        """Middleware to validate UUIDs globally before processing any request."""
        for key in request.view_args or {}:
            if key.endswith("_id"):  # Only validate keys ending with "_id"
                try:
                    request.view_args[key] = UUID(request.view_args[key])
                except (ValueError, TypeError):
                    return jsonify({"error": f"Resource not found"}), 404

    return app


def register_blueprints(app):
    """Register all application blueprints"""
    from app.modules.auth.urls import register_auth_routes
    from app.modules.user.urls import users_routes
    from app.modules.category.urls import categories_routes
    from app.modules.transaction.urls import transactions_routes
    from app.modules.saving_plan.urls import saving_plans_routes
    from app.modules.budget.urls import budget_routes
    from app.modules.transaction_summary_report.urls import reports_routes
    from app.modules.recurring_transaction.urls import recurring_transaction_routes

    register_auth_routes(app)
    users_routes(app)
    categories_routes(app)
    transactions_routes(app)
    saving_plans_routes(app)
    reports_routes(app)
    budget_routes(app)
    recurring_transaction_routes(app)
