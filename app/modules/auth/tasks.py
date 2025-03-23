from app.celery_app import celery
from app.core.logger import logger
import os
from app.core.mail import send_email


@celery.task(name="send_password_reset_email", bind=True, max_retries=3)
def send_password_reset_email(self, email, reset_url):
    try:
        # Get template ID from environment variables
        template_id = os.environ.get("PASSWORD_RESET_TEMPLATE_ID")

        # Base template data with reset URL
        template_data = {"reset_url": reset_url, "subject": "Reset Your Password"}

        # Use imported send_email function
        send_email(
            to_email=email,
            subject="Reset Your Password",
            template_id=template_id,
            template_data=template_data,
        )

        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        self.retry(exc=e, countdown=60 * self.request.retries)


@celery.task(name="send_verification_email", bind=True, max_retries=3)
def send_verification_email(self, email, verification_url):

    try:
        # Get template ID from environment variables
        template_id = os.environ.get("EMAIL_VERIFICATION_TEMPLATE_ID")

        # Base template data with verification URL
        template_data = {
            "verification_url": verification_url,
            "subject": "Verify Your Email",
        }

        # Use imported send_email function
        send_email(
            to_email=email,
            subject="Verify Your Email",
            template_id=template_id,
            template_data=template_data,
        )

        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        self.retry(exc=e, countdown=60 * self.request.retries)
