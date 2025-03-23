from flask import request
from flask_restful import Resource
from app.core.permissions import permission_required, admin_only
from app.extensions import db
from app.modules.saving_plan.models import SavingPlan
from app.modules.saving_plan.schemas import SavingPlanSchema, SavingPlanUpdateSchema
from app.core.authentication import authenticated_user
from app.core.pagination import paginate
from marshmallow import ValidationError
from app.core.responses import validation_error_response
from functools import wraps
from app.core.decorators import handle_errors
from app.core.utils import BaseListResource

saving_plans_schemas = SavingPlanSchema(many=True)


class AllSavingPlanResource(BaseListResource):
    method_decorators = [
        handle_errors,
        admin_only,
        authenticated_user,
    ]

    model = SavingPlan
    schema = saving_plans_schemas
    endpoint = "saving_plans.all-saving-plans"


class SavingPlanListResource(Resource):
    def __init__(self):
        self.schema = SavingPlanSchema()
        self.schemas = SavingPlanSchema(many=True)

    @authenticated_user
    @permission_required(SavingPlan)
    def get(self, user_id):
        """Get all saving plans for a user"""
        saving_plans = SavingPlan.query.filter_by(user_id=user_id, is_deleted=False)
        return (
            paginate(
                query=saving_plans,
                schema=self.schemas,
                endpoint="saving_plans.saving-plans",
            ),
            200,
        )

    @authenticated_user
    @permission_required(SavingPlan)
    @handle_errors
    def post(self, user_id):
        """Create a new saving plan for a user"""
        data = request.get_json()
        data["user_id"] = user_id
        saving_plan = self.schema.load(data)
        db.session.add(saving_plan)
        db.session.commit()
        return self.schema.dump(saving_plan), 201


class SavingPlanResource(Resource):
    def __init__(self):
        self.schema = SavingPlanSchema()
        self.update_schema = SavingPlanUpdateSchema()

    @authenticated_user
    @permission_required(resource_model=SavingPlan, resource_param="saving_plan_id")
    def get(self, user_id, saving_plan_id):
        """Get a specific saving plan"""
        saving_plan = SavingPlan.query.get_or_404(saving_plan_id)
        return self.schema.dump(saving_plan), 200

    @authenticated_user
    @permission_required(SavingPlan, resource_param="saving_plan_id")
    @handle_errors
    def patch(self, user_id, saving_plan_id):
        """Update a saving plan"""
        saving_plan = SavingPlan.query.get_or_404(saving_plan_id)
        data = request.get_json()
        self.update_schema.context["instance"] = saving_plan
        saving_plan = self.update_schema.load(data, instance=saving_plan, partial=True)
        db.session.commit()
        return self.schema.dump(saving_plan), 200

    @authenticated_user
    @permission_required(resource_model=SavingPlan, resource_param="saving_plan_id")
    def delete(self, user_id, saving_plan_id):
        """Delete a saving plan"""
        saving_plan = SavingPlan.query.get_or_404(saving_plan_id)
        saving_plan.is_deleted = True
        db.session.commit()
        return {}, 204
