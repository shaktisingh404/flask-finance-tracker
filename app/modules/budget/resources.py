from flask_restful import Resource
from flask import request, g
from marshmallow import ValidationError

from app.extensions import db
from .models import Budget
from .schemas import BudgetSchema, BudgetUpdateSchema
from .services import (
    get_user_budgets,
    create_budget,
    update_budget,
)
from app.core.permissions import permission_required, admin_only
from app.core.authentication import authenticated_user
from app.core.responses import validation_error_response
from app.core.pagination import paginate
from app.core.logger import logger
from app.core.decorators import handle_errors
from copy import deepcopy
from app.core.utils import BaseListResource


# Create schema instances
budget_schema = BudgetSchema()
budgets_schema = BudgetSchema(many=True)
budget_update_schema = BudgetUpdateSchema()


class AllBudgetListResource(BaseListResource):
    method_decorators = [
        handle_errors,
        admin_only,
        authenticated_user,
    ]
    model = Budget
    schema = budgets_schema
    endpoint = "budget.all-budgets"


class BudgetListResource(Resource):
    """Resource for listing and creating budgets"""

    method_decorators = [
        handle_errors,
        permission_required(Budget),
        authenticated_user,
    ]

    def get(self, user_id):
        query_params = {
            "category_id": request.args.get("category_id"),
            "month": request.args.get("month"),
            "year": request.args.get("year"),
        }
        logger.info(f"Budget list requested by user {user_id}")
        query = get_user_budgets(user_id, query_params)

        result = paginate(
            query=query,
            schema=budgets_schema,
            endpoint="budget.budgets",
        )
        return result, 200

    def post(self, user_id):
        """
        Create a new budget.
        """
        data = request.get_json() or {}
        data["user_id"] = user_id
        logger.info("Creating budget")
        budget = budget_schema.load(data)
        # Create budget through service
        budget = create_budget(budget)
        if isinstance(budget, tuple) and len(budget) == 2:
            return budget

        return budget_schema.dump(budget), 201


class BudgetDetailResource(Resource):
    method_decorators = [
        handle_errors,
        permission_required(Budget, resource_param="budget_id"),
        authenticated_user,
    ]

    def get(self, user_id, budget_id):
        """
        Get a specific budget.
        """
        budget = Budget.query.get(budget_id)
        result = budget_schema.dump(budget)
        logger.info(f"Retrieved budget {budget.id}")
        return result, 200

    def patch(self, user_id, budget_id):
        """
        Update a specific budget(only amount of the budget can be updated).
        """

        budget = Budget.query.get(budget_id)
        old_budget = deepcopy(budget)
        data = request.get_json() or {}
        logger.info(f"Updating budget {budget.id}")
        updated_budget = budget_update_schema.load(data, instance=budget, partial=True)
        budget = update_budget(updated_budget, old_budget)
        if isinstance(budget, tuple) and len(budget) == 2:
            return budget
        logger.info(f"Updated budget {budget.id}")
        return budget_schema.dump(budget), 200

    def delete(self, user_id, budget_id):
        """
        Delete (soft-delete) a specific budget.
        """
        budget = Budget.query.get(budget_id)
        budget.is_deleted = True
        db.session.commit()
        logger.info(f"Deleted budget {budget.id}")
        return {}, 204
