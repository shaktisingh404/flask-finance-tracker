# from flask import g, request
# from flask_restful import Resource
# from marshmallow import ValidationError
# from sqlalchemy import func
# from app.core.authentication import authenticated_user
# from app.modules.transaction.models import Transaction
# from app.modules.category.models import Category
# from app.core.constants import TransactionType
# from app.modules.transaction_summary_report.schemas import SummaryReportQuerySchema
# from app.core.permissions import permission_required
# from app.core.decorators import handle_errors
# from datetime import datetime, timedelta
# from sqlalchemy import desc
# from app.core.constants import TransactionType
# from app.modules.category.models import Category
# from app.modules.saving_plan.models import SavingPlan
# from .tasks import email_transaction_history

# summary_report_schema = SummaryReportQuerySchema()

# from flask_restful import Resource
# from app.core.authentication import authenticated_user
# from app.core.permissions import permission_required
# from app.core.decorators import handle_errors
# from app.modules.transaction.models import Transaction
# from .schemas import SummaryReportQuerySchema


# class BaseReportResource(Resource):
#     schema = SummaryReportQuerySchema()

#     def get_base_query(self, user_id):
#         """Get base query with filters"""
#         query_params = self.schema.load(request.args)
#         base_filters = [
#             Transaction.user_id == user_id,
#             Transaction.transaction_at.between(
#                 query_params["start_date"], query_params["end_date"]
#             ),
#             Transaction.is_deleted == False,
#         ]
#         return Transaction.query.filter(*base_filters), query_params


# class TransactionReportResource(BaseReportResource):
#     @authenticated_user
#     @permission_required(Transaction)
#     @handle_errors
#     def get(self, user_id):
#         """Get detailed transaction report"""
#         query, query_params = self.get_base_query(user_id)

#         credit_trans = query.filter(Transaction.type == TransactionType.CREDIT.value)
#         debit_trans = query.filter(Transaction.type == TransactionType.DEBIT.value)
#         savings_trans = query.join(SavingPlan).filter(SavingPlan.is_deleted == False)

#         report = {
#             "start_date": query_params["start_date"].isoformat(),
#             "end_date": query_params["end_date"].isoformat(),
#             "total_credit": float(),
#             "total_debit": float(
#                 debit_trans.with_entities(func.sum(Transaction.amount)).scalar() or 0
#             ),
#             "transactions": {
#                 "credit": [
#                     {
#                         "id": str(t.id),
#                         "amount": float(t.amount),
#                         "category_id": str(t.category.id if t.category else None),
#                         "category_name": t.category.name if t.category else None,
#                         "description": t.description,
#                         "transaction_at": t.transaction_at.isoformat(),
#                     }
#                     for t in credit_trans.order_by(
#                         desc(Transaction.transaction_at)
#                     ).all()
#                 ],
#                 "debit": [
#                     {
#                         "id": str(t.id),
#                         "amount": float(t.amount),
#                         "category_id": str(t.category.id if t.category else None),
#                         "category_name": t.category.name if t.category else None,
#                         "description": t.description,
#                         "transaction_at": t.transaction_at.isoformat(),
#                     }
#                     for t in debit_trans.order_by(
#                         desc(Transaction.transaction_at)
#                     ).all()
#                 ],
#                 "savings_plan": [
#                     {
#                         "id": str(t.id),
#                         "amount": float(t.amount),
#                         "plan_id": str(t.saving_plan.id),
#                         "plan_name": t.saving_plan.name,
#                         "description": t.description,
#                         "transaction_at": t.transaction_at.isoformat(),
#                     }
#                     for t in savings_trans.order_by(
#                         desc(Transaction.transaction_at)
#                     ).all()
#                 ],
#             },
#         }

#         for t_type in TransactionType:
#             total = float(
#                 query.filter(Transaction.type == t_type.value)
#                 .outerjoin(SavingPlan)
#                 .filter(SavingPlan.id == None)
#                 .with_entities(func.sum(Transaction.amount))
#                 .scalar()
#                 or 0
#             )
#             if t_type == TransactionType.CREDIT:
#                 report["total_credit"] = total
#             else:
#                 report["total_debit"] = total

#         return report, 200


# class TrendsReportResource(BaseReportResource):
#     def get(self, user_id):
#         """Get spending trends report"""
#         query, query_params = self.get_base_query(user_id)

#         # Initialize response structure
#         trends = {
#             "start_date": query_params["start_date"].isoformat(),
#             "end_date": query_params["end_date"].isoformat(),
#             "total_credit": 0,
#             "total_debit": 0,
#             "categories": [],
#             "savings_plan": [],
#         }

#         # Calculate totals for credit and debit (excluding savings plans)
#         for t_type in TransactionType:
#             total = float(
#                 query.filter(Transaction.type == t_type.value)
#                 .outerjoin(SavingPlan)
#                 .filter(SavingPlan.id == None)
#                 .with_entities(func.sum(Transaction.amount))
#                 .scalar()
#                 or 0
#             )

#             if t_type == TransactionType.CREDIT:
#                 trends["total_credit"] = total
#             else:
#                 trends["total_debit"] = total

#         # Calculate data for each category
#         category_data = []
#         categories = (
#             Category.query.join(Transaction)
#             .filter(Transaction.user_id == user_id, Category.is_deleted == False)
#             .distinct()
#             .all()
#         )

#         for category in categories:
#             credit_amount = float(
#                 query.filter(
#                     Transaction.type == TransactionType.CREDIT.value,
#                     Transaction.category_id == category.id,
#                 )
#                 .outerjoin(SavingPlan)
#                 .filter(SavingPlan.id == None)
#                 .with_entities(func.sum(Transaction.amount))
#                 .scalar()
#                 or 0
#             )

#             debit_amount = float(
#                 query.filter(
#                     Transaction.type == TransactionType.DEBIT.value,
#                     Transaction.category_id == category.id,
#                 )
#                 .outerjoin(SavingPlan)
#                 .filter(SavingPlan.id == None)
#                 .with_entities(func.sum(Transaction.amount))
#                 .scalar()
#                 or 0
#             )

#             if credit_amount > 0 or debit_amount > 0:
#                 category_data.append(
#                     {
#                         "id": str(category.id),
#                         "name": category.name,
#                         "credit": round(credit_amount, 2),
#                         "debit": round(debit_amount, 2),
#                         "credit_percentage": round(
#                             (
#                                 (credit_amount / trends["total_credit"] * 100)
#                                 if trends["total_credit"]
#                                 else 0
#                             ),
#                             2,
#                         ),
#                         "debit_percentage": round(
#                             (
#                                 (debit_amount / trends["total_debit"] * 100)
#                                 if trends["total_debit"]
#                                 else 0
#                             ),
#                             2,
#                         ),
#                     }
#                 )

#         trends["categories"] = category_data

#         # Calculate savings plan data
#         savings_total = float(
#             query.join(SavingPlan)
#             .filter(SavingPlan.is_deleted == False)
#             .with_entities(func.sum(Transaction.amount))
#             .scalar()
#             or 0
#         )

#         saving_plans = (
#             SavingPlan.query.join(Transaction)
#             .filter(Transaction.user_id == user_id, SavingPlan.is_deleted == False)
#             .group_by(SavingPlan.id, SavingPlan.name)
#             .with_entities(
#                 SavingPlan.id,
#                 SavingPlan.name,
#                 func.sum(Transaction.amount).label("total"),
#             )
#             .all()
#         )

#         trends["savings_plan"] = [
#             {
#                 "id": str(plan.id),
#                 "name": plan.name,
#                 "amount": float(plan.total),
#                 "percentage": round(
#                     (float(plan.total) / savings_total * 100) if savings_total else 0, 2
#                 ),
#             }
#             for plan in saving_plans
#         ]

#         return trends, 200


# class EmailTransactionReportResource(BaseReportResource):
#     """API resource for emailing transaction history reports."""

#     @authenticated_user
#     @permission_required(Transaction)
#     @handle_errors
#     def get(self, user_id):
#         """
#         Send transaction history report via email.
#         Supports CSV and PDF formats.
#         """
#         try:
#             # Get file format from query params, default to CSV
#             file_format = request.args.get("file_format", "csv").lower()
#             if file_format not in ["csv", "pdf"]:
#                 return {"message": 'Invalid format. Use "csv" or "pdf"'}, 400

#             # Get transaction data using base query
#             query, query_params = self.get_base_query(user_id)

#             # Check if transactions exist
#             if not query.first():
#                 return {"message": "No transactions found"}, 404
#             # Queue email task (assuming you have Celery configured)
#             email_transaction_history.delay(
#                 user_id=user_id,
#                 email=g.current_user.email,
#                 start_date=query_params["start_date"].isoformat(),
#                 end_date=query_params["end_date"].isoformat(),
#                 file_format=file_format,
#             )

#             return {
#                 "message": "Transaction history report will be sent to your email"
#             }, 200

#         except ValidationError as err:
#             return {"message": "Validation error", "errors": err.messages}, 400

# app/modules/transaction/resources.py
from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError
from app.core.authentication import authenticated_user
from app.core.permissions import permission_required
from app.core.decorators import handle_errors
from app.modules.transaction.models import Transaction
from .schemas import SummaryReportQuerySchema
from .services import TransactionReportService
from .tasks import email_transaction_history


class BaseReportResource(Resource):
    schema = SummaryReportQuerySchema()

    def get_base_params(self, user_id):
        data = request.args.copy()
        data["user_id"] = user_id
        return self.schema.load(data)


class TransactionReportResource(BaseReportResource):
    @authenticated_user
    @permission_required(Transaction)
    @handle_errors
    def get(self, user_id):
        """Get detailed transaction report"""
        query_params = self.get_base_params(user_id)  # Pass user_id here
        report = TransactionReportService.get_transaction_report(
            query_params["user_id"],
            query_params["start_date"],
            query_params["end_date"],
        )
        return report, 200


class TrendsReportResource(BaseReportResource):
    @authenticated_user
    @permission_required(Transaction)
    @handle_errors
    def get(self, user_id):
        """Get spending trends report"""
        query_params = self.get_base_params(user_id)
        trends = TransactionReportService.get_trends_report(
            query_params["user_id"],
            query_params["start_date"],
            query_params["end_date"],
        )
        return trends, 200


class EmailTransactionReportResource(BaseReportResource):
    @authenticated_user
    @permission_required(Transaction)
    @handle_errors
    def get(self, user_id):
        """Send transaction history report via email"""

        file_format = request.args.get("file_format", "csv").lower()
        if file_format not in ["csv", "pdf"]:
            return {"message": 'Invalid format. Use "csv" or "pdf"'}, 400

        query_params = self.get_base_params(user_id)  # Pass user_id here
        base_query = Transaction.query.filter(
            Transaction.user_id == query_params["user_id"],  # Use validated user_id
            Transaction.transaction_at.between(
                query_params["start_date"], query_params["end_date"]
            ),
            Transaction.is_deleted == False,
        )

        if not base_query.first():
            return {"message": "No transactions found"}, 404

        email_transaction_history.delay(
            user_id=query_params["user_id"],  # Use validated user_id
            email=g.current_user.email,
            start_date=query_params["start_date"].isoformat(),
            end_date=query_params["end_date"].isoformat(),
            file_format=file_format,
        )

        return {"message": "Transaction history report will be sent to your email"}, 200
