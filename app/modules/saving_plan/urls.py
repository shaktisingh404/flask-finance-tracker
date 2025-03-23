from flask import Blueprint
from flask_restful import Api
from app.modules.saving_plan.resources import (
    SavingPlanListResource,
    SavingPlanResource,
    AllSavingPlanResource,
)

# Create a blueprint for the users module
saving_plan_bp = Blueprint("saving_plans", __name__)
saving_plan_api = Api(saving_plan_bp)

# Add resources to the API
saving_plan_api.add_resource(
    SavingPlanListResource, "/<user_id>/saving_plans", endpoint="saving-plans"
)
saving_plan_api.add_resource(
    AllSavingPlanResource, "/saving_plans", endpoint="all-saving-plans"
)
saving_plan_api.add_resource(
    SavingPlanResource,
    "/<user_id>/saving_plans/<saving_plan_id>",
    endpoint="saving-plan",
)


# Function to initialize routes
def saving_plans_routes(app):
    app.register_blueprint(saving_plan_bp, url_prefix="/api/users")
