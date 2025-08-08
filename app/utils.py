import os
import re
import io
from datetime import datetime

from flask import flash, current_app
from flask_mail import Message
from smtplib import SMTPException

from .docx_generator import generate_docx
from . import mail

def flash_success(message):
    flash(message, 'success')

def flash_error(message):
    flash(message, 'danger')


def send_email(subject, recipients, body, attachments=None):
    """Send an email using the configured Flask-Mail extension.

    Parameters
    ----------
    subject: str
        Subject line for the message.
    recipients: list[str]
        List of recipient email addresses.
    body: str
        Plain text body of the message.
    attachments: iterable[tuple[str, str, bytes]], optional
        Iterable of ``(filename, content_type, data)`` tuples representing
        attachments to include in the message.

    Returns
    -------
    tuple[datetime | None, str]
        A tuple containing the time the email was sent (``None`` on
        failure) and a status string (``"sent"`` or ``"error"``).
    """

    msg = Message(
        subject,
        recipients=recipients,
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
    )
    msg.body = body
    if attachments:
        for filename, content_type, data in attachments:
            msg.attach(filename, content_type, data)

    status = "error"
    sent_at = None
    try:
        mail.send(msg)
        sent_at = datetime.utcnow()
        status = "sent"
    except SMTPException as exc:
        current_app.logger.error("Failed to send email: %s", exc)
    return sent_at, status


def build_docx_filename(zajecia):
    """Return a sanitized filename for the DOCX report of ``zajecia``."""

    beneficjenci = zajecia.beneficjenci
    first_name = beneficjenci[0].imie if beneficjenci else "beneficjent"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", first_name)
    safe_specjalista = re.sub(r"[^A-Za-z0-9_.-]", "_", zajecia.specjalista)
    date_str = zajecia.data.strftime("%Y-%m-%d")
    return f"Konsultacje z {safe_specjalista} {date_str} {safe_name}.docx"


def send_session_docx(zajecia, recipient, subject="Raport zajęć"):
    """Generate a DOCX report for ``zajecia`` and send it via email."""

    beneficjenci = zajecia.beneficjenci
    filename = build_docx_filename(zajecia)

    buffer = io.BytesIO()
    try:
        generate_docx(zajecia, beneficjenci, buffer)
    except FileNotFoundError as exc:
        current_app.logger.error("Failed to generate session document: %s", exc)
        return None, "error"

    attachments = [
        (
            filename,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            buffer.getvalue(),
        )
    ]

    return send_email(subject, [recipient], "", attachments=attachments)
