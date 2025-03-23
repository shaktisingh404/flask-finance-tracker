from flask import request, g
from flask_restful import Resource
from app.extensions import db
from app.modules.transaction.models import Transaction
from app.modules.transaction.schemas import TransactionSchema, TransactionUpdateSchema
from app.core.authentication import authenticated_user
from app.core.permissions import permission_required, admin_only
from app.core.logger import logger
from app.core.pagination import paginate
from app.modules.transaction.services import (
    SavingPlanTransactionService,
    BudgetTransactionService,
)
from app.core.constants import TransactionType
from app.core.decorators import handle_errors
from copy import deepcopy
from app.core.utils import BaseListResource

# Initialize schemas
transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)
transaction_update_schema = TransactionUpdateSchema()


class AllTransactionsResource(BaseListResource):
    method_decorators = [
        handle_errors,
        admin_only,
        authenticated_user,
    ]

    model = Transaction
    schema = transactions_schema
    endpoint = "transactions.all_transactions"
    type_enum = TransactionType


class TransactionListResource(Resource):
    method_decorators = [
        handle_errors,
        permission_required(Transaction),
        authenticated_user,
    ]

    def get(self, user_id):
        """List all transactions based on user role and query params."""
        logger.info(f"Fetching transactions for user: {g.current_user.id}")

        queryset = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
        ).order_by(Transaction.created_at.desc())
        transaction_type = request.args.get("type")
        if transaction_type and transaction_type in TransactionType.__members__:
            queryset = queryset.filter(Transaction.type == transaction_type)
        result = paginate(
            query=queryset,
            schema=transactions_schema,
            endpoint="transactions.transactions",
        )
        logger.info(
            f"Transactions retrieved successfully for user: {g.current_user.id}"
        )
        return result, 200

    def post(self, user_id):
        """Create a new transaction."""
        logger.info("Creating new transaction for user")
        data = request.get_json()
        data["user_id"] = user_id
        transaction_schema.context["user_id"] = user_id
        transaction = transaction_schema.load(data)
        SavingPlanTransactionService.update_saving_plan_on_transaction_created(
            transaction
        )

        if transaction.type == TransactionType.DEBIT:
            BudgetTransactionService.update_budget_on_transaction_created(transaction)
        db.session.add(transaction)
        db.session.commit()
        logger.info(f"Transaction created successfully: {transaction.id}")
        return transaction_schema.dump(transaction), 201


class TransactionDetailResource(Resource):
    method_decorators = [
        handle_errors,
        permission_required(Transaction, resource_param="transaction_id"),
        authenticated_user,
    ]

    def get(self, user_id, transaction_id):
        """Retrieve a specific transaction."""
        transaction = Transaction.query.get_or_404(transaction_id)
        logger.info(f"Transaction retrieved successfully: {transaction_id}")
        return transaction_schema.dump(transaction), 200

    def patch(self, user_id, transaction_id):
        """Update a specific transaction."""

        transaction = Transaction.query.get_or_404(transaction_id)
        logger.info(f"Updating transaction: {transaction_id}")
        data = request.get_json()

        # Create a copy of original transaction for comparison
        old_transaction = deepcopy(transaction)

        updated_transaction = transaction_update_schema.load(
            data, instance=transaction, partial=True
        )
        SavingPlanTransactionService.update_saving_plan_on_transaction_updated(
            updated_transaction, old_transaction
        )
        BudgetTransactionService.update_budget_on_transaction_updated(
            updated_transaction, old_transaction
        )
        db.session.commit()
        logger.info(f"Transaction updated successfully: {transaction_id}")
        return transaction_schema.dump(updated_transaction), 200

    def delete(self, user_id, transaction_id):
        """Soft-delete a specific transaction and update associated saving plan."""
        transaction = Transaction.query.get_or_404(transaction_id)

        # Update saving plan and budget
        SavingPlanTransactionService.update_saving_plan_on_transaction_deleted(
            transaction
        )
        BudgetTransactionService.update_budget_on_transaction_deleted(transaction)
        transaction.is_deleted = True

        # Commit the transaction
        db.session.commit()
        logger.info(f"Transaction deleted successfully: {transaction_id}")
        return {}, 204
