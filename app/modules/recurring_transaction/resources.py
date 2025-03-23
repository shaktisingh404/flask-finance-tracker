from flask import request, g
from flask_restful import Resource
from marshmallow import ValidationError
from app.extensions import db
from .models import RecurringTransaction
from app.modules.transaction.schemas import TransactionSchema, TransactionUpdateSchema
from app.core.authentication import authenticated_user
from app.core.decorators import validate_json_request
from app.core.responses import validation_error_response
from app.core.permissions import permission_required, admin_only
from app.core.logger import logger
from app.core.pagination import paginate
from .schemas import RecurringTransactionSchema
from app.core.utils import BaseListResource
from app.core.constants import TransactionType
from app.core.decorators import handle_errors
from copy import deepcopy

recurring_transactions_schemas = RecurringTransactionSchema(many=True)


class AllRecurringTransactionResource(BaseListResource):
    method_decorators = [
        handle_errors,
        admin_only,
        authenticated_user,
    ]

    model = RecurringTransaction
    schema = recurring_transactions_schemas
    endpoint = "recurring_transaction.all-recurring-transactions"


class RecurringTransactionListResource(Resource):
    method_decorators = [
        handle_errors,
        permission_required(RecurringTransaction),
        authenticated_user,
    ]

    def __init__(self):
        self.schema = RecurringTransactionSchema()
        self.schemas = RecurringTransactionSchema(many=True)

    def get(self, user_id):
        """Get all recurring for a user"""
        recurring_transactions = RecurringTransaction.query.filter_by(
            user_id=user_id, is_deleted=False
        )
        return (
            paginate(
                query=recurring_transactions,
                schema=self.schemas,
                endpoint="recurring_transaction.recurring-transactions",
            ),
            200,
        )

    def post(self, user_id):
        logger.info(f"User {user_id} creating a new recurring transaction.")
        data = request.get_json()
        data["user_id"] = user_id
        recurring_transaction = self.schema.load(data)
        recurring_transaction.next_transaction_at = recurring_transaction.starts_at
        db.session.add(recurring_transaction)
        db.session.commit()
        logger.info(
            f"User {user_id} created a new recurring transaction {recurring_transaction.id}."
        )
        return self.schema.dump(recurring_transaction), 201


class RecurringTransactionResource(Resource):
    method_decorators = [
        handle_errors,
        permission_required(
            RecurringTransaction, resource_param="recurring_transaction_id"
        ),
        authenticated_user,
    ]

    def __init__(self):
        self.schema = RecurringTransactionSchema()

    def get(self, user_id, recurring_transaction_id):
        """Retrieve specific recurring transaction"""
        recurring_transaction = RecurringTransaction.query.get_or_404(
            recurring_transaction_id
        )
        logger.info(f"User {user_id} retrieved transaction {recurring_transaction_id}.")
        return self.schema.dump(recurring_transaction)

    def patch(self, user_id, recurring_transaction_id):
        """Update specific recurring transaction"""

        recurring_transaction = RecurringTransaction.query.get_or_404(
            recurring_transaction_id
        )
        data = self.schema.load(
            request.get_json(),
            instance=recurring_transaction,
            partial=True,
            context={"request": request},
        )
        updated_transaction = self.schema.update(recurring_transaction, data)
        db.session.commit()

        logger.info(
            f"User {request.user.id} updated transaction {recurring_transaction_id}."
        )
        return self.schema.dump(updated_transaction)

    def delete(self, user_id, recurring_transaction_id):
        """Soft delete recurring transaction"""

        recurring_transaction = self._get_object(recurring_transaction_id)
        recurring_transaction.is_deleted = True
        db.session.commit()

        logger.info(
            f"User {request.user.id} deleted transaction {recurring_transaction_id}."
        )
        return {}, 204
