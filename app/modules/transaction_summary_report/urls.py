from flask import Blueprint
from flask_restful import Api
from app.modules.transaction_summary_report.resources import (
    TransactionReportResource,
    TrendsReportResource,
    EmailTransactionReportResource,
)

# Create a Blueprint for transaction reports
transaction_reports_bp = Blueprint("transaction-reports", __name__)

# Create an API instance
transaction_reports_api = Api(transaction_reports_bp)

# Register resources with the API
transaction_reports_api.add_resource(
    TransactionReportResource, "/summary", endpoint="transactionreportresource"
)
transaction_reports_api.add_resource(
    TrendsReportResource, "/trends", endpoint="trendsreportresource"
)
transaction_reports_api.add_resource(
    EmailTransactionReportResource, "/export", endpoint="emailtransactionreportresource"
)


# Function to initialize routes
def reports_routes(app):
    app.register_blueprint(
        transaction_reports_bp, url_prefix="/api/users/<user_id>/transaction-reports"
    )
