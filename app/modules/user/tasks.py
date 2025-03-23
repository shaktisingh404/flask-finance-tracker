import os
from app.celery_app import celery
from app.core.constants import EmailChangeConstants
from app.core.logger import logger
from app.core.mail import send_email
from app.modules.user.models import User, UserRelationship
from app.modules.category.models import Category
from app.modules.transaction.models import Transaction
from app.extensions import db
from app.modules.budget.models import Budget
from app.modules.recurring_transaction.models import RecurringTransaction
from app.modules.saving_plan.models import SavingPlan

# Get configuration from environment variables
CURRENT_EMAIL_TEMPLATE_ID = os.environ.get("CURRENT_EMAIL_TEMPLATE_ID")
NEW_EMAIL_TEMPLATE_ID = os.environ.get("NEW_EMAIL_TEMPLATE_ID")
STAFF_CHANGE_TEMPLATE_ID = os.environ.get("STAFF_CHANGE_TEMPLATE_ID")


@celery.task(name="send_email_change_otp_pair", bind=True, max_retries=3)
def send_email_change_otp_pair(
    self, current_email, new_email, current_email_otp, new_email_otp
):
    """Send OTPs for email change to both current and new emails"""
    try:
        # Validate required environment variables
        if not all([CURRENT_EMAIL_TEMPLATE_ID, NEW_EMAIL_TEMPLATE_ID]):
            raise ValueError(
                "Missing required email template IDs in environment variables"
            )

        # Send OTP to current email
        current_template_data = {
            "current_email_otp": current_email_otp,
            "otp_validity_minutes": int(EmailChangeConstants.OTP_VALIDITY_SECONDS / 60)
            + 1,
        }

        send_email(
            to_email=current_email,
            subject="Verify your current email address",
            template_id=CURRENT_EMAIL_TEMPLATE_ID,
            template_data=current_template_data,
        )

        # Send OTP to new email
        new_template_data = {
            "new_email_otp": new_email_otp,
            "otp_validity_minutes": int(EmailChangeConstants.OTP_VALIDITY_SECONDS / 60)
            + 1,
        }

        send_email(
            to_email=new_email,
            subject="Verify your new email address",
            template_id=NEW_EMAIL_TEMPLATE_ID,
            template_data=new_template_data,
        )

        logger.info(f"Email change OTPs sent to {current_email} and {new_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email change OTPs: {str(e)}", exc_info=True)
        # Retry with exponential backoff
        retry_in = 60 * (2**self.request.retries)
        raise self.retry(exc=e, countdown=retry_in)


@celery.task(name="send_staff_email_verification", max_retries=3, bind=True)
def send_staff_email_verification(self, new_email, verification_url, username):
    """Send email verification for staff email change"""
    try:
        # Validate required environment variable
        if not STAFF_CHANGE_TEMPLATE_ID:
            raise ValueError(
                "Missing staff change template ID in environment variables"
            )

        template_data = {
            "username": username,
            "verification_url": verification_url,
            "validity_hours": int(EmailChangeConstants.OTP_VALIDITY_SECONDS / 3600),
        }

        send_email(
            to_email=new_email,
            subject="Verify your email address change",
            template_id=STAFF_CHANGE_TEMPLATE_ID,
            template_data=template_data,
        )

        logger.info(f"Email change verification sent to {new_email}")
        return True

    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}", exc_info=True)
        # Retry with exponential backoff
        retry_in = 60 * (2**self.request.retries)
        raise self.retry(exc=e, countdown=retry_in)


@celery.task(name="delete_associated_data", bind=True, max_retries=3)
def delete_associated_data(self, user_id):
    """Delete all associated data for a user and their child if exists"""
    try:

        def soft_delete_user_data(user_id):
            """Helper function to soft delete all data associated with a user"""
            models_to_delete = [
                Category,
                Transaction,
                Budget,
                RecurringTransaction,
                SavingPlan,
            ]

            for model in models_to_delete:
                model.query.filter_by(user_id=user_id, is_deleted=False).update(
                    {"is_deleted": True}
                )

        # Delete parent user's data
        soft_delete_user_data(user_id)

        # Handle child user if exists
        user = User.query.get(user_id)
        child = user.get_child()
        if child:
            soft_delete_user_data(child.id)
            User.query.filter_by(id=child.id).update({"is_deleted": True})
            UserRelationship.query.filter_by(child_id=child.id).update(
                {"is_deleted": True}
            )
        db.session.commit()
        logger.info(f"Deleted associated data for user {user}")
        return True

    except Exception as e:
        logger.error(f"Error deleting associated data: {str(e)}", exc_info=True)
        retry_in = 60 * (2**self.request.retries)
        raise self.retry(exc=e, countdown=retry_in)
