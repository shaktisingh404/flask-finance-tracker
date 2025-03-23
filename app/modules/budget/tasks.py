import os
from app.core.logger import logger
from app.celery_app import celery
from app.modules.budget.models import Budget
from app.modules.category.models import Category
from app.modules.user.models import User
from decimal import Decimal
import calendar
from app.core.mail import send_email
from python_http_client.exceptions import BadRequestsError
from app.core.constants import (
    BUDGET_WARNING_THRESHOLD,
    BUDGET_EXCEEDED_THRESHOLD,
    BUDGET_EXCEEDED_KEYWORD,
    BUDGET_WARNING_KEYWORD,
)


BUDGET_WARNING_TEMPLATE_ID = os.getenv("BUDGET_WARNING_TEMPLATE_ID")
BUDGET_EXCEEDED_TEMPLATE_ID = os.getenv("BUDGET_EXCEEDED_TEMPLATE_ID")


def _retry_if_possible(task, exception: Exception) -> None:
    """Handle retry logic for Celery tasks."""
    if task.request.retries < task.max_retries:
        task.retry(exc=exception, countdown=60 * (task.request.retries + 1))


@celery.task(name="check_budget_thresholds", bind=True, max_retries=3)
def check_budget_thresholds(self, budget_id: int) -> bool:
    try:
        budget = Budget.query.get(budget_id)
        if not budget:
            logger.warning(f"Budget not found for threshold check: {budget_id}")
            return False

        percentage_used = budget.percentage_used
        budget.reset_notification_flags(percentage_used)  # Reset flags if needed
        notification_type = _determine_notification_type(percentage_used, budget)

        if not notification_type:
            return False

        logger.info(
            f"Budget {budget.id} {notification_type} threshold reached: {percentage_used}%"
        )

        send_budget_notification.delay(budget.id, notification_type, percentage_used)
        return True

    except Exception as e:
        logger.error(f"Error checking budget thresholds for ID {budget_id}: {str(e)}")
        _retry_if_possible(self, e)
        return False


@celery.task(name="send_budget_notification", bind=True, max_retries=3)
def send_budget_notification(
    self, budget_id: int, notification_type: str, percentage: float = None
) -> bool:
    try:
        budget, user, category = _fetch_required_data(budget_id, notification_type)

        month_name = calendar.month_name[budget.month]
        percentage = percentage or budget.percentage_used

        email_data = _prepare_base_email_data(budget, user, category, month_name)
        _customize_email_data(
            email_data, notification_type, budget, category, percentage
        )

        send_email_data(**email_data)

        # Update the flag using the model method
        budget.set_notification_sent(notification_type)

        logger.info(
            f"Sent budget {notification_type} notification to {user.email} for budget {budget_id}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Error sending {notification_type} notification for budget {budget_id}: {str(e)}"
        )
        _retry_if_possible(self, e)
        return False


def send_email_data(recipient: str, subject: str, template: str, **kwargs) -> None:
    if not all([recipient, subject, template]):
        raise ValueError("Recipient, subject, and template are required")

    template_data = kwargs  # Pass all kwargs as template data

    try:
        send_email(
            to_email=recipient,
            subject=subject,
            template_id=_get_template_id(template),
            template_data=template_data,
        )
        logger.debug(f"Email sent to {recipient} with subject: {subject}")
    except BadRequestsError as e:
        logger.error(f"SendGrid API error sending email to {recipient}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        raise


def _determine_notification_type(percentage_used: float, budget: Budget) -> str | None:
    """Determine the type of notification based on percentage used and flags."""
    if (
        percentage_used >= BUDGET_EXCEEDED_THRESHOLD
        and not budget.exceeded_notification_sent
    ):
        return BUDGET_EXCEEDED_KEYWORD
    elif (
        BUDGET_WARNING_THRESHOLD <= percentage_used < BUDGET_EXCEEDED_THRESHOLD
        and not budget.warning_notification_sent
    ):
        return BUDGET_WARNING_KEYWORD
    return None


def _fetch_required_data(
    budget_id: int, notification_type: str
) -> tuple[Budget, User, Category]:
    """Fetch and validate required data for notification."""
    budget = Budget.query.get(budget_id)
    if not budget:
        raise ValueError(
            f"Budget not found for {notification_type} notification: {budget_id}"
        )

    user = User.query.get(budget.user_id)
    if not user or not user.email:
        raise ValueError(f"User not found or no email for budget {budget_id}")

    category = Category.query.get(budget.category_id)
    if not category:
        raise ValueError(f"Category not found for budget {budget_id}")

    return budget, user, category


def _prepare_base_email_data(
    budget: Budget, user: User, category: Category, month_name: str
) -> dict:
    return {
        "recipient": user.email,
        "category_name": category.name,
        "month_name": month_name,
        "year": budget.year,
        "budget_amount": float(budget.amount),
        "spent_amount": float(budget.spent_amount),
    }


def _customize_email_data(
    email_data: dict,
    notification_type: str,
    budget: Budget,
    category: Category,
    percentage: float,
) -> None:
    if notification_type == BUDGET_WARNING_KEYWORD:
        email_data.update(
            {
                "subject": f"Budget Warning: {category.name} budget is at {percentage}%",
                "template": "warning",
                "remaining": float(budget.remaining),
                "percentage": float(percentage),
            }
        )
    elif notification_type == BUDGET_EXCEEDED_KEYWORD:
        email_data.update(
            {
                "subject": f"Budget Alert: {category.name} budget has been exceeded!",
                "template": "exceeded",
                "overspent": float(
                    max(Decimal("0"), budget.spent_amount - budget.amount)
                ),
            }
        )
    else:
        raise ValueError(f"Invalid notification type: {notification_type}")


def _get_template_id(template: str) -> str:
    template_mapping = {
        "warning": BUDGET_WARNING_TEMPLATE_ID,
        "exceeded": BUDGET_EXCEEDED_TEMPLATE_ID,
    }
    return template_mapping.get(
        template,
    )
