import re
from io import BytesIO
from datetime import datetime

from flask import flash, abort, current_app
from flask_mail import Message
from smtplib import SMTPException

from .docx_generator import generate_docx
from . import mail

def flash_success(message):
    flash(message, 'success')

def flash_error(message):
    flash(message, 'danger')

def get_object_or_404(model, id):
    obj = model.query.get(id)
    if obj is None:
        abort(404)
    return obj

def validate_form(form):
    if form.validate_on_submit():
        return True
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", "danger")
    return False


def build_docx_filename(zajecia):
    """Build a safe DOCX filename for a given session."""

    def sanitize(value):
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    beneficjenci = zajecia.beneficjenci
    first_name = beneficjenci[0].imie if beneficjenci else "beneficjent"
    date_str = zajecia.data.strftime("%Y-%m-%d")
    return "Konsultacje z {} {} {}.docx".format(
        sanitize(zajecia.specjalista),
        date_str,
        sanitize(first_name),
    )


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

    beneficjenci = zajecia.beneficjenci
    filename = build_docx_filename(zajecia)

    status = "error"
    sent_at = None
    output = BytesIO()
    try:
        generate_docx(zajecia, beneficjenci, output)
        msg = Message(
            subject,
            recipients=[recipient],
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )
        msg.attach(
            filename,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            output.getvalue(),
        )
        mail.send(msg)
        sent_at = datetime.utcnow()
        status = "sent"
    except (FileNotFoundError, SMTPException) as exc:
        current_app.logger.error("Failed to send session document: %s", exc)

    return sent_at, status
