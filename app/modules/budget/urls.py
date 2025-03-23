from flask import Blueprint
from flask_restful import Api
from .resources import BudgetListResource, BudgetDetailResource, AllBudgetListResource

budget_bp = Blueprint("budget", __name__)
budget_api = Api(budget_bp)

# Register endpoints
budget_api.add_resource(AllBudgetListResource, "/budgets", endpoint="all-budgets")
budget_api.add_resource(BudgetListResource, "/<user_id>/budgets", endpoint="budgets")
budget_api.add_resource(
    BudgetDetailResource, "/<user_id>/budgets/<budget_id>", endpoint="budget-detail"
)


# Function to initialize routes
def budget_routes(app):
    app.register_blueprint(budget_bp, url_prefix="/api/users")
