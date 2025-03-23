from flask import Blueprint
from flask_restful import Api
from .resources import (
    RecurringTransactionListResource,
    RecurringTransactionResource,
    AllRecurringTransactionResource,
)

# Create a blueprint for the users module
recurring_transaction_bp = Blueprint("recurring_transactions", __name__)
recurring_transaction_api = Api(recurring_transaction_bp)

# Add resources to the API
recurring_transaction_api.add_resource(
    RecurringTransactionListResource,
    "/<user_id>/recurring-transactions",
    endpoint="recurring-transactions",
)
recurring_transaction_api.add_resource(
    AllRecurringTransactionResource,
    "/recurring-transactions",
    endpoint="all-recurring-transactions",
)
recurring_transaction_api.add_resource(
    RecurringTransactionResource,
    "/<user_id>/recurring-transactions/<recurring_transaction_id>",
    endpoint="recurring-transaction",
)


# Function to initialize routes
def recurring_transaction_routes(app):
    app.register_blueprint(
        recurring_transaction_bp,
        url_prefix="/api/users",
    )
