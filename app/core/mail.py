# from app.core.logger import logger
# import os
# from typing import Dict, Any, Optional
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail


# # def send_email(to_email, subject, template_id, template_data):

# #     try:
# #         from_email = os.environ.get("FROM_EMAIL")
# #         message = Mail(from_email=from_email, to_emails=to_email, subject=subject)
# #         message.template_id = template_id
# #         message.dynamic_template_data = template_data
# #         sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
# #         response = sg.send(message)
# #         logger.info(f"Email sent to {to_email} with status {response.status_code}")
# #         return True
# #     except Exception as e:
# #         logger.error(f"Failed to send email to {to_email}: {str(e)}")
# #         raise

# from app.core.logger import logger
# import os
# import base64
# from typing import Dict, Any, Optional, List, Tuple
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import (
#     Mail,
#     Attachment,
#     FileContent,
#     FileName,
#     FileType,
#     Disposition,
# )


# def send_email(
#     to_email: str,
#     subject: str,
#     template_id: Optional[str] = None,
#     template_data: Optional[Dict[str, Any]] = None,
#     body: Optional[str] = None,
#     attachments: Optional[List[Tuple[str, str, str]]] = None,
# ) -> bool:
#     """
#     Send an email using SendGrid

#     Args:
#         to_email: Recipient email address
#         subject: Email subject
#         template_id: SendGrid template ID (optional)
#         template_data: Data for template (optional)
#         body: Plain text email body (optional)
#         attachments: List of tuples (filename, mime_type, content) (optional)

#     Returns:
#         bool: True if email was sent successfully
#     """
#     try:
#         from_email = os.environ.get("FROM_EMAIL")
#         message = Mail(from_email=from_email, to_emails=to_email, subject=subject)

#         # Add template if provided
#         if template_id:
#             message.template_id = template_id
#             if template_data:
#                 message.dynamic_template_data = template_data
#         # Add plain text body if provided
#         elif body:
#             message.plain_text_content = body

#         # Add attachments if provided
#         if attachments:
#             for filename, mime_type, content in attachments:
#                 encoded_file = base64.b64encode(
#                     content.encode() if isinstance(content, str) else content
#                 ).decode()

#                 attachment = Attachment()
#                 attachment.file_content = FileContent(encoded_file)
#                 attachment.file_type = FileType(mime_type)
#                 attachment.file_name = FileName(filename)
#                 attachment.disposition = Disposition("attachment")

#                 message.attachment = attachment

#         # Send email
#         sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
#         response = sg.send(message)

#         logger.info(f"Email sent to {to_email} with status {response.status_code}")
#         return True

#     except Exception as e:
#         logger.error(f"Failed to send email to {to_email}: {str(e)}")
#         raise

# app/core/mail.py
from app.core.logger import logger
import os
import base64
from typing import Dict, Any, Optional, List, Tuple
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
)
from python_http_client.exceptions import BadRequestsError


def send_email(
    to_email: str,
    subject: str,
    template_id: Optional[str] = None,
    template_data: Optional[Dict[str, Any]] = None,
    body: Optional[str] = None,
    attachments: Optional[List[Tuple[str, str, str]]] = None,
) -> bool:
    """
    Send an email using SendGrid.

    Args:
        to_email: Recipient email address
        subject: Email subject (used in template_data for dynamic templates)
        template_id: SendGrid template ID (optional)
        template_data: Data for template (optional)
        body: Plain text email body (optional, used if no template_id)
        attachments: List of tuples (filename, mime_type, content) (optional)

    Returns:
        bool: True if email was sent successfully

    Raises:
        ValueError: If required parameters are missing
        BadRequestsError: If SendGrid API rejects the request
    """
    if not to_email:
        raise ValueError("Recipient email is required")

    try:
        from_email = os.environ.get("FROM_EMAIL")
        if not from_email:
            raise ValueError("FROM_EMAIL environment variable not set")

        message = Mail(from_email=from_email, to_emails=to_email)

        # Handle dynamic template case
        if template_id:
            if not template_data:
                template_data = {}
            # Ensure subject is in template_data for dynamic templates
            template_data["subject"] = subject
            message.template_id = template_id
            message.dynamic_template_data = template_data
            logger.debug(
                f"Sending dynamic template email: template_id={template_id}, data={template_data}"
            )
        # Handle plain text case
        else:
            raise ValueError("Either template_id or body must be provided")

        # Add attachments if provided
        if attachments:
            for filename, mime_type, content in attachments:
                encoded_file = base64.b64encode(
                    content.encode() if isinstance(content, str) else content
                ).decode()

                attachment = Attachment(
                    file_content=FileContent(encoded_file),
                    file_type=FileType(mime_type),
                    file_name=FileName(filename),
                    disposition=Disposition("attachment"),
                )
                message.add_attachment(attachment)

        # Send email
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        response = sg.send(message)

        logger.info(f"Email sent to {to_email} with status {response.status_code}")
        return True

    except BadRequestsError as e:
        logger.error(
            f"SendGrid API error sending email to {to_email}: {str(e)} - Response: {e.body}"
        )
        raise
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise
