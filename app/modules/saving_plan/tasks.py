import os
from datetime import datetime, timedelta
from celery import shared_task
from app.extensions import db
from app.modules.saving_plan.models import SavingPlan
from app.modules.user.models import User
from app.core.mail import send_email
from app.modules.transaction.models import Transaction
from app.core.constants import Frequency, SavingPlanStatus
from app.celery_app import celery
from sqlalchemy import func
from decimal import Decimal

TEMPLATE_ID = os.environ.get("CURRENT_EMAIL_TEMPLATE_ID")
SAVING_PLAN_COMPLETED = os.environ.get("SAVING_PLAN_COMPLETED")
SAVINGS_PLAN_CREATED = os.environ.get("SAVINGS_PLAN_CREATED")
SAVINGS_PLAN_DATE_EXTENDED = os.environ.get("SAVINGS_PLAN_DATE_EXTENDED")


@celery.task
def check_overdue_savings_plans():
    """Check for overdue savings plans and apply the hybrid auto-extension approach."""
    today = datetime.today().date()

    # Query overdue active plans
    overdue_plans = SavingPlan.query.filter(
        SavingPlan.current_deadline < today,
        SavingPlan.is_deleted == False,
        SavingPlan.status == SavingPlanStatus.ACTIVE,
    ).all()

    for plan in overdue_plans:
        # Calculate total saved amount
        total_saved = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.saving_plan_id == plan.id
        ).scalar() or Decimal("0")

        # Check if target reached
        if total_saved >= plan.amount:
            plan.status = SavingPlanStatus.COMPLETED
            db.session.commit()
            send_savings_plan_completion_notification.delay(plan.id)
            continue

        # Determine extension period
        auto_extend_days = (
            30
            if plan.frequency == Frequency.MONTHLY
            else 7 if plan.frequency == Frequency.WEEKLY else 365
        )
        new_deadline = plan.current_deadline + timedelta(days=auto_extend_days)

        # Send notification email
        template_data = {
            "user_name": plan.user.name,
            "plan_name": plan.name,
            "deadline": plan.current_deadline.strftime("%Y-%m-%d"),
            "new_deadline": new_deadline.strftime("%Y-%m-%d"),
            "target_amount": f"{float(plan.amount):,.2f}",
            "total_saved": f"{float(total_saved):,.2f}",
            "remaining_amount": f"{float(plan.amount - total_saved):,.2f}",
            "message": f"Your savings plan deadline has passed, and we are extending it automatically to {new_deadline.strftime('%Y-%m-%d')}.",
        }

        send_email(
            to_email=plan.user.email,
            subject=f"Your Savings Plan {plan.name} Deadline Passed - Auto-Extension in Progress",
            template_id=SAVINGS_PLAN_DATE_EXTENDED,
            template_data=template_data,
        )

        # Update deadline
        plan.current_deadline = new_deadline
        db.session.commit()


@celery.task
def check_savings_progress():
    """Monitor savings progress and send alerts if behind schedule."""
    today = datetime.today().date()

    active_plans = SavingPlan.query.filter(
        SavingPlan.is_deleted == False,
        SavingPlan.status == SavingPlanStatus.ACTIVE,
        SavingPlan.current_deadline >= today,
    ).all()

    for plan in active_plans:
        total_saved = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.saving_plan_id == plan.id
        ).scalar() or Decimal("0")

        remaining_amount = plan.amount - total_saved
        days_remaining = (plan.current_deadline - today).days

        if days_remaining <= 0 or remaining_amount <= 0:
            continue

        # Calculate required savings per period
        if plan.frequency == Frequency.MONTHLY:
            remaining_periods = max((days_remaining + 29) // 30, 1)
            period_start = today.replace(day=1)
        elif plan.frequency == Frequency.WEEKLY:
            remaining_periods = max((days_remaining + 6) // 7, 1)
            period_start = today - timedelta(days=today.weekday())
        else:
            remaining_periods = max(days_remaining, 1)
            period_start = today

        required_per_period = remaining_amount / remaining_periods

        # Calculate current period savings
        period_savings = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.saving_plan_id == plan.id,
            Transaction.transaction_at >= period_start,
            Transaction.transaction_at <= today,
        ).scalar() or Decimal("0")

        if period_savings < required_per_period:
            template_data = {
                "user_name": plan.user.name,
                "plan_name": plan.name,
                "target_amount": f"{float(plan.amount):,.2f}",
                "total_saved": f"{float(total_saved):,.2f}",
                "remaining_amount": f"{float(remaining_amount):,.2f}",
                "required_per_period": f"{float(required_per_period):,.2f}",
                "saved_this_period": f"{float(period_savings):,.2f}",
                "frequency": plan.frequency.value.lower(),
                "days_remaining": days_remaining,
                "message": f"You need to save {required_per_period:.2f} per {plan.frequency.value.lower()} to meet your goal by {plan.current_deadline}",
            }

            send_email(
                to_email=plan.user.email,
                subject=f"Reminder: You need to save {required_per_period:.2f} for {plan.name}",
                template_id=TEMPLATE_ID,
                template_data=template_data,
            )


@celery.task(name="send_savings_plan_completion_notification", bind=True, max_retries=3)
def send_savings_plan_completion_notification(self, savings_plan_id):
    saving_plan = SavingPlan.query.get(savings_plan_id)
    user_name = saving_plan.user.name
    target_amount = saving_plan.amount
    saved_amount = saving_plan.saved_amount
    template_data = {
        "target_amount": target_amount,
        "total_saved": saved_amount,
        "user_name": user_name,
    }
    send_email(
        to_email=saving_plan.user.email,
        subject="Savings has been completed",
        template_id=SAVING_PLAN_COMPLETED,
        template_data=template_data,
    )


@celery.task(name="saving_plan_creation_notificaion", bind=True, max_retries=3)
def saving_plan_creation_notificaion(self, savings_plan_id):
    saving_plan = SavingPlan.query.get(savings_plan_id)

    user_name = saving_plan.user.name
    template_data = {
        "user_name": user_name,
        "plan_name": saving_plan.name,
        "target_amount": f"{float(saving_plan.target_amount):,.2f}",
        "frequency": saving_plan.frequency,
        "deadline": saving_plan.current_deadline.strftime("%Y-%m-%d"),
    }
    send_email(
        to_email=saving_plan.user.email,
        subject="Savings Plan Created",
        template_id=SAVINGS_PLAN_CREATED,
        template_data=template_data,
    )
