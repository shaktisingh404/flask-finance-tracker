from marshmallow import Schema, fields, ValidationError, validates_schema, pre_load
from app.extensions import ma
from app.modules.user.models import User
from marshmallow import EXCLUDE
from app.core.constants import UserRole
from app.extensions import db
import uuid


class SummaryReportQuerySchema(ma.Schema):
    """Schema for validating summary report query parameters"""

    class Meta:
        unknown = EXCLUDE

    user_id = fields.UUID(required=True)  # Changed from fields.Int to fields.UUID
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)

    @pre_load
    def check_admin_role(self, data, **kwargs):
        """Check if the user with the given user_id is an admin"""
        user_id = data.get("user_id")
        if user_id:
            # Convert user_id to string if it's not already, for database query
            user = db.session.query(User).filter_by(id=str(user_id)).first()
            if user and user.role == UserRole.ADMIN:
                raise ValidationError(
                    {"user": "Admin users are not allowed to generate reports"}
                )
        return data

    @validates_schema
    def validate_all(self, data, **kwargs):
        """Combined validation for all fields"""
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError(
                    {
                        "start_date": ["Must be before end_date"],
                        "end_date": ["Must be after start_date"],
                    }
                )
        return data
