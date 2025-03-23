# from sqlalchemy import func
# from app.modules.transaction.models import Transaction
# from app.modules.category.models import Category
# from app.modules.saving_plan.models import SavingPlan
# from app.core.constants import TransactionType
# from datetime import datetime


# class TransactionReportService:
#     @staticmethod
#     def get_transaction_report(user_id, start_date, end_date):
#         """Generate detailed transaction report"""
#         base_query = Transaction.query.filter(
#             Transaction.user_id == user_id,
#             Transaction.transaction_at.between(start_date, end_date),
#             Transaction.is_deleted == False,
#         )

#         credit_trans = base_query.filter(
#             Transaction.type == TransactionType.CREDIT.value
#         )
#         debit_trans = base_query.filter(Transaction.type == TransactionType.DEBIT.value)
#         savings_trans = base_query.join(SavingPlan).filter(
#             SavingPlan.is_deleted == False
#         )

#         report = {
#             "start_date": start_date.isoformat(),
#             "end_date": end_date.isoformat(),
#             "total_credit": 0.0,
#             "total_debit": 0.0,
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
#                         Transaction.transaction_at.desc()
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
#                         Transaction.transaction_at.desc()
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
#                         Transaction.transaction_at.desc()
#                     ).all()
#                 ],
#             },
#         }

#         for t_type in TransactionType:
#             total = float(
#                 base_query.filter(Transaction.type == t_type.value)
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

#         return report

#     @staticmethod
#     def get_trends_report(user_id, start_date, end_date):
#         """Generate spending trends report"""
#         base_query = Transaction.query.filter(
#             Transaction.user_id == user_id,
#             Transaction.transaction_at.between(start_date, end_date),
#             Transaction.is_deleted == False,
#         )

#         trends = {
#             "start_date": start_date.isoformat(),
#             "end_date": end_date.isoformat(),
#             "total_credit": 0.0,
#             "total_debit": 0.0,
#             "categories": [],
#             "savings_plan": [],
#         }

#         # Calculate totals
#         for t_type in TransactionType:
#             total = float(
#                 base_query.filter(Transaction.type == t_type.value)
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

#         # Category data
#         categories = (
#             Category.query.join(Transaction)
#             .filter(Transaction.user_id == user_id, Category.is_deleted == False)
#             .distinct()
#             .all()
#         )

#         category_data = []
#         for category in categories:
#             credit_amount = float(
#                 base_query.filter(
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
#                 base_query.filter(
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

#         # Savings plan data
#         savings_total = float(
#             base_query.join(SavingPlan)
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

#         return trends

from sqlalchemy import func
from app.modules.transaction.models import Transaction
from app.modules.category.models import Category
from app.modules.saving_plan.models import SavingPlan
from app.core.constants import TransactionType
from datetime import datetime


class TransactionReportService:
    @staticmethod
    def get_transaction_report(user_id, start_date, end_date):
        """Generate detailed transaction report"""
        base_query = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_at.between(start_date, end_date),
            Transaction.is_deleted == False,
        )

        # Exclude savings plan transactions from credit/debit calculations
        regular_transactions = base_query.outerjoin(SavingPlan).filter(
            SavingPlan.id == None
        )

        credit_trans = regular_transactions.filter(
            Transaction.type == TransactionType.CREDIT.value
        )
        debit_trans = regular_transactions.filter(
            Transaction.type == TransactionType.DEBIT.value
        )

        # Separate query for savings plan transactions
        savings_trans = base_query.join(SavingPlan).filter(
            SavingPlan.is_deleted == False
        )

        # Get all relevant categories
        categories = (
            Category.query.join(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_at.between(start_date, end_date),
                Transaction.is_deleted == False,
                Category.is_deleted == False,
            )
            .distinct()
            .all()
        )

        # Create category summaries
        credit_by_category = {}
        debit_by_category = {}

        # Process credit transactions by category
        for category in categories:
            credit_amount = float(
                credit_trans.filter(Transaction.category_id == category.id)
                .with_entities(func.sum(Transaction.amount))
                .scalar()
                or 0
            )

            if credit_amount > 0:
                credit_by_category[str(category.id)] = {
                    "category_id": str(category.id),
                    "category_name": category.name,
                    "total_amount": credit_amount,
                    "transaction_count": credit_trans.filter(
                        Transaction.category_id == category.id
                    ).count(),
                }

        # Process debit transactions by category
        for category in categories:
            debit_amount = float(
                debit_trans.filter(Transaction.category_id == category.id)
                .with_entities(func.sum(Transaction.amount))
                .scalar()
                or 0
            )

            if debit_amount > 0:
                debit_by_category[str(category.id)] = {
                    "category_id": str(category.id),
                    "category_name": category.name,
                    "total_amount": debit_amount,
                    "transaction_count": debit_trans.filter(
                        Transaction.category_id == category.id
                    ).count(),
                }

        # Handle transactions without categories
        credit_no_category = float(
            credit_trans.filter(Transaction.category_id == None)
            .with_entities(func.sum(Transaction.amount))
            .scalar()
            or 0
        )

        if credit_no_category > 0:
            credit_by_category["no_category"] = {
                "category_id": None,
                "category_name": "Uncategorized",
                "total_amount": credit_no_category,
                "transaction_count": credit_trans.filter(
                    Transaction.category_id == None
                ).count(),
            }

        debit_no_category = float(
            debit_trans.filter(Transaction.category_id == None)
            .with_entities(func.sum(Transaction.amount))
            .scalar()
            or 0
        )

        if debit_no_category > 0:
            debit_by_category["no_category"] = {
                "category_id": None,
                "category_name": "Uncategorized",
                "total_amount": debit_no_category,
                "transaction_count": debit_trans.filter(
                    Transaction.category_id == None
                ).count(),
            }

        # Summarize savings plans
        savings_by_plan = {}
        saving_plans = (
            SavingPlan.query.join(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_at.between(start_date, end_date),
                Transaction.is_deleted == False,
                SavingPlan.is_deleted == False,
            )
            .group_by(SavingPlan.id, SavingPlan.name)
            .with_entities(
                SavingPlan.id,
                SavingPlan.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .all()
        )

        for plan in saving_plans:
            savings_by_plan[str(plan.id)] = {
                "plan_id": str(plan.id),
                "plan_name": plan.name,
                "total_amount": float(plan.total),
                "transaction_count": plan.count,
            }

        # Calculate totals for regular transactions only (no saving plans)
        total_credit = float(
            credit_trans.with_entities(func.sum(Transaction.amount)).scalar() or 0
        )
        total_debit = float(
            debit_trans.with_entities(func.sum(Transaction.amount)).scalar() or 0
        )

        report = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_credit": total_credit,
            "total_debit": total_debit,
            "summary": {
                "credit_by_category": list(credit_by_category.values()),
                "debit_by_category": list(debit_by_category.values()),
                "savings_by_plan": list(savings_by_plan.values()),
            },
        }

        return report

    @staticmethod
    def get_trends_report(user_id, start_date, end_date):
        """Generate spending trends report"""
        base_query = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_at.between(start_date, end_date),
            Transaction.is_deleted == False,
        )

        trends = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_credit": 0.0,
            "total_debit": 0.0,
            "categories": [],
            "savings_plan": [],
        }

        # Calculate totals
        for t_type in TransactionType:
            total = float(
                base_query.filter(Transaction.type == t_type.value)
                .outerjoin(SavingPlan)
                .filter(SavingPlan.id == None)
                .with_entities(func.sum(Transaction.amount))
                .scalar()
                or 0
            )
            if t_type == TransactionType.CREDIT:
                trends["total_credit"] = total
            else:
                trends["total_debit"] = total

        # Category data
        categories = (
            Category.query.join(Transaction)
            .filter(Transaction.user_id == user_id, Category.is_deleted == False)
            .distinct()
            .all()
        )

        category_data = []
        for category in categories:
            credit_amount = float(
                base_query.filter(
                    Transaction.type == TransactionType.CREDIT.value,
                    Transaction.category_id == category.id,
                )
                .outerjoin(SavingPlan)
                .filter(SavingPlan.id == None)
                .with_entities(func.sum(Transaction.amount))
                .scalar()
                or 0
            )

            debit_amount = float(
                base_query.filter(
                    Transaction.type == TransactionType.DEBIT.value,
                    Transaction.category_id == category.id,
                )
                .outerjoin(SavingPlan)
                .filter(SavingPlan.id == None)
                .with_entities(func.sum(Transaction.amount))
                .scalar()
                or 0
            )

            if credit_amount > 0 or debit_amount > 0:
                category_data.append(
                    {
                        "id": str(category.id),
                        "name": category.name,
                        "credit": round(credit_amount, 2),
                        "debit": round(debit_amount, 2),
                        "credit_percentage": round(
                            (
                                (credit_amount / trends["total_credit"] * 100)
                                if trends["total_credit"]
                                else 0
                            ),
                            2,
                        ),
                        "debit_percentage": round(
                            (
                                (debit_amount / trends["total_debit"] * 100)
                                if trends["total_debit"]
                                else 0
                            ),
                            2,
                        ),
                    }
                )

        trends["categories"] = category_data

        # Savings plan data
        savings_total = float(
            base_query.join(SavingPlan)
            .filter(SavingPlan.is_deleted == False)
            .with_entities(func.sum(Transaction.amount))
            .scalar()
            or 0
        )

        saving_plans = (
            SavingPlan.query.join(Transaction)
            .filter(Transaction.user_id == user_id, SavingPlan.is_deleted == False)
            .group_by(SavingPlan.id, SavingPlan.name)
            .with_entities(
                SavingPlan.id,
                SavingPlan.name,
                func.sum(Transaction.amount).label("total"),
            )
            .all()
        )

        trends["savings_plan"] = [
            {
                "id": str(plan.id),
                "name": plan.name,
                "amount": float(plan.total),
                "percentage": round(
                    (float(plan.total) / savings_total * 100) if savings_total else 0, 2
                ),
            }
            for plan in saving_plans
        ]

        return trends
