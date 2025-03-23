from flask import Blueprint
from flask_restful import Api
from app.modules.transaction.resources import (
    TransactionListResource,
    TransactionDetailResource,
    AllTransactionsResource,
)


transaction_bp = Blueprint("transactions", __name__)
transaction_api = Api(transaction_bp)

transaction_api.add_resource(
    TransactionListResource, "/<user_id>/transactions", endpoint="transactions"
)
transaction_api.add_resource(
    AllTransactionsResource, "/transactions", endpoint="all_transactions"
)
transaction_api.add_resource(
    TransactionDetailResource,
    "/<user_id>/transactions/<transaction_id>",
    endpoint="transaction",
)


# Function to initialize routes
def transactions_routes(app):
    app.register_blueprint(transaction_bp, url_prefix="/api/users")
