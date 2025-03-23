import io
import os
import csv
from decimal import Decimal
from datetime import datetime
from celery import shared_task
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from app.extensions import db
from app.core.mail import send_email
from app.modules.transaction.models import Transaction
from app.modules.user.models import User
from app.core.constants import TransactionType
from flask import current_app
from app.celery_app import celery

TRANSACTION_SUMMARY_REPORT = os.getenv("TRANSACTION_SUMMARY_REPORT")


class TransactionReport:
    """Handles creating transaction reports with savings plans handling"""

    def __init__(self, start_date, end_date, transactions):
        self.start_date = start_date
        self.end_date = end_date
        self.transactions = transactions

        self.categorized_credits = [
            t for t in transactions if t.type == TransactionType.CREDIT and t.category
        ]
        self.categorized_debits = [
            t for t in transactions if t.type == TransactionType.DEBIT and t.category
        ]
        self.savings_plans = [
            t
            for t in transactions
            if t.type == TransactionType.CREDIT and not t.category
        ]

        self.total_credits = Decimal(
            sum(float(t.amount) for t in self.categorized_credits)
        )
        self.total_debits = Decimal(
            sum(float(t.amount) for t in self.categorized_debits)
        )
        self.total_savings = Decimal(sum(float(t.amount) for t in self.savings_plans))
        self.net_balance = self.total_credits - self.total_debits

    def generate_csv(self):
        """Creates CSV report with savings plan names from t.saving_plan"""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["Transaction History Report"])
        writer.writerow([f"Period: {self.start_date} to {self.end_date}"])
        writer.writerow(
            [f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
        )
        writer.writerow([])

        writer.writerow(["Summary"])
        writer.writerow(["Metric", "Amount"])
        writer.writerow(["Total Credits (Categorized)", f"{self.total_credits:.2f}"])
        writer.writerow(["Total Debits (Categorized)", f"{self.total_debits:.2f}"])
        writer.writerow(["Total Savings Plans", f"{self.total_savings:.2f}"])
        writer.writerow(["Net Balance (Excl. Savings)", f"{self.net_balance:.2f}"])
        writer.writerow([])

        for trans_type, transactions in [
            ("Credit Transactions (Categorized)", self.categorized_credits),
            ("Debit Transactions (Categorized)", self.categorized_debits),
            ("Savings Plan Deposits", self.savings_plans),
        ]:
            writer.writerow([trans_type])
            writer.writerow(
                [
                    "Date",
                    "Category/Savings Plan",
                    "Amount",
                    "Description",
                ]
            )
            for t in transactions:
                # Use t.saving_plan for savings plan name, fall back to "Unnamed" if not available
                savings_name = (
                    t.saving_plan.name
                    if (not t.category and hasattr(t, "saving_plan") and t.saving_plan)
                    else "Unnamed Savings Plan"
                )
                writer.writerow(
                    [
                        t.transaction_at.strftime("%Y-%m-%d"),
                        t.category.name if t.category else savings_name,
                        f"{float(t.amount):.2f}",  # No rupee symbol
                        t.description or "No description",
                    ]
                )
            writer.writerow([])

        output.seek(0)
        return output.getvalue()

    def generate_pdf(self):
        """Creates PDF report with savings plan names from t.saving_plan"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
        )

        styles = getSampleStyleSheet()
        elements = []

        header_style = ParagraphStyle(
            "Header",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#2C3E50"),
            spaceAfter=12,
        )

        subheader_style = ParagraphStyle(
            "Subheader",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#34495E"),
            spaceAfter=8,
        )

        elements.append(Paragraph("Transaction History Report", header_style))
        elements.append(
            Paragraph(f"Period: {self.start_date} to {self.end_date}", styles["Normal"])
        )
        elements.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 0.25 * inch))

        summary_data = [
            ["Description", "Amount"],
            ["Total Credits (Categorized)", f"{self.total_credits:.2f}"],
            ["Total Debits (Categorized)", f"{self.total_debits:.2f}"],
            ["Total Savings Plans", f"{self.total_savings:.2f}"],
            ["Net Balance (Excl. Savings)", f"{self.net_balance:.2f}"],
        ]

        summary_table = Table(summary_data, colWidths=[3.5 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ECF0F1")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    # ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("BOX", (0, 0), (-1, -1), 1, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 0.25 * inch))

        for title, transactions, color in [
            ("Credit Transactions (Categorized)", self.categorized_credits, "#27AE60"),
            ("Debit Transactions (Categorized)", self.categorized_debits, "#E74C3C"),
            ("Savings Plan Deposits", self.savings_plans, "#2980B9"),
        ]:
            if transactions:
                elements.append(Paragraph(title, subheader_style))

                data = [["Date", "Category/Savings Plan", "Amount", "Description"]]
                for t in transactions:
                    # Use t.saving_plan for savings plan name, fall back to "Unnamed" if not available
                    savings_name = (
                        t.saving_plan.name
                        if (
                            not t.category
                            and hasattr(t, "saving_plan")
                            and t.saving_plan
                        )
                        else "Unnamed Savings Plan"
                    )
                    data.append(
                        [
                            t.transaction_at.strftime("%Y-%m-%d"),
                            t.category.name if t.category else savings_name,
                            f"{float(t.amount):.2f}",  # No rupee symbol
                            t.description or "No description",
                        ]
                    )

                t = Table(data, colWidths=[1.5 * inch, 1.5 * inch, 1 * inch, 2 * inch])
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(color)),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            (
                                "BACKGROUND",
                                (0, 1),
                                (-1, -1),
                                colors.HexColor("#F9FAFB"),
                            ),
                            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                            ("BOX", (0, 0), (-1, -1), 1, colors.black),
                            ("PADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                elements.append(t)
                elements.append(Spacer(1, 0.2 * inch))

        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content


@celery.task(bind=True)
def email_transaction_history(self, user_id, email, start_date, end_date, file_format):
    try:
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User not found with id {user_id}")

        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_at.between(start_date, end_date),
            Transaction.is_deleted == False,
        ).all()

        if not transactions:
            return {"status": "error", "message": "No transactions found"}

        report = TransactionReport(start_date, end_date, transactions)

        if file_format.lower() == "csv":
            report_data = report.generate_csv()
            mime_type = "text/csv"
            filename = f"transactions_{start_date}_{end_date}.csv"
            report_data = report_data.encode("utf-8")
        elif file_format.lower() == "pdf":
            report_data = report.generate_pdf()
            mime_type = "application/pdf"
            filename = f"transactions_{start_date}_{end_date}.pdf"
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

        template_data = {
            "user_name": user.name,
            "start_date": start_date,
            "end_date": end_date,
        }

        send_email(
            to_email=email,
            subject="Transaction History Report",
            template_id=TRANSACTION_SUMMARY_REPORT,
            template_data=template_data,
            attachments=[(filename, mime_type, report_data)],
        )

        return {"status": "success", "message": "Report sent successfully"}

    except Exception as e:
        current_app.logger.error(f"Failed to send transaction report: {str(e)}")
        raise self.retry(exc=e, countdown=60 * 5)
