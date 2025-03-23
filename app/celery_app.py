from celery.schedules import crontab
from celery import Celery
import os

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB = os.getenv("REDIS_DB")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"


def make_celery(app=None):
    """
    Create a Celery instance that integrates with Flask application context.
    """

    celery = Celery(
        "app",
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=[
            "app.modules.user.tasks",
            "app.modules.auth.tasks",
            "app.modules.saving_plan.tasks",
            "app.modules.transaction_summary_report.tasks",
            "app.modules.recurring_transaction.tasks",
            "app.modules.budget.tasks",
        ],
    )

    # Use Redis URL from environment if available
    celery.conf.broker_url = CELERY_BROKER_URL
    celery.conf.result_backend = CELERY_RESULT_BACKEND

    # Configure Celery
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        task_track_started=True,
        worker_max_tasks_per_child=1000,
        task_acks_late=True,
    )

    celery.conf.beat_schedule = {
        "process-recurring-transactions": {
            "task": "app.modules.recurring_transaction.tasks.process_recurring_transactions",
            "schedule": crontab(minute="*/1"),
        },
        "update-savings-plan-deadlines": {
            "task": "app.modules.saving_plan.tasks.check_overdue_savings_plans",
            "schedule": crontab(hour=0, minute=0),  # Run daily at midnight
        },
        "send-savings-reminders": {
            "task": "app.modules.saving_plan.tasks.check_savings_progress",
            "schedule": crontab(hour=22, minute=0),  # Run daily at 10 PM
        },
    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            if app:
                with app.app_context():
                    return self.run(*args, **kwargs)
            else:
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery()
