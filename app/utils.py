import os
import re
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

def validate_form(form):
    if form.validate_on_submit():
        return True
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", "danger")
    return False


def send_session_docx(zajecia, recipient, subject="Raport zajęć"):
    """Generate a DOCX report for ``zajecia`` and send it via email.

    Parameters
    ----------
    zajecia: Zajecia
        Session for which the document should be generated.
    recipient: str
        Email address of the recipient.
    subject: str, optional
        Subject of the email. Defaults to ``"Raport zajęć"``.

    Returns
    -------
    tuple[datetime | None, str]
        A tuple containing the time the email was sent (``None`` on
        failure) and a status string (``"sent"`` or ``"error"``).
    """

    output_dir = os.path.join(current_app.root_path, "static", "docx")
    os.makedirs(output_dir, exist_ok=True)

    beneficjenci = zajecia.beneficjenci
    first_name = beneficjenci[0].imie if beneficjenci else "beneficjent"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", first_name)
    safe_specjalista = re.sub(r"[^A-Za-z0-9_.-]", "_", zajecia.specjalista)
    date_str = zajecia.data.strftime("%Y-%m-%d")
    filename = f"Konsultacje z {safe_specjalista} {date_str} {safe_name}.docx"
    output_path = os.path.join(output_dir, filename)

    status = "error"
    sent_at = None
    try:
        generate_docx(zajecia, beneficjenci, output_path)
        msg = Message(
            subject,
            recipients=[recipient],
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )
        with open(output_path, "rb") as f:
            msg.attach(
                filename,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                f.read(),
            )
        mail.send(msg)
        sent_at = datetime.utcnow()
        status = "sent"
    except (FileNotFoundError, SMTPException) as exc:
        current_app.logger.error("Failed to send session document: %s", exc)
    finally:
        try:
            os.remove(output_path)
        except OSError:
            current_app.logger.warning(
                "Failed to remove generated DOCX %s", output_path
            )

    return sent_at, status
