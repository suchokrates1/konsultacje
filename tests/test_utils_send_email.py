from datetime import datetime
from smtplib import SMTPException

from app.utils import send_email


def test_send_email_with_attachment(monkeypatch, app):
    """send_email returns timestamp and 'sent' status with an attachment."""
    def fake_send(message):
        return None

    monkeypatch.setattr("app.utils.mail.send", fake_send)

    with app.app_context():
        sent_at, status = send_email(
            "Subject",
            ["dest@example.com"],
            "Body",
            attachments=[("file.txt", "text/plain", b"data")],
        )

    assert status == "sent"
    assert isinstance(sent_at, datetime)


def test_send_email_handles_smtp_exception(monkeypatch, app):
    """send_email returns error status and no timestamp when sending fails."""
    def fake_send(message):
        raise SMTPException("fail")

    monkeypatch.setattr("app.utils.mail.send", fake_send)

    with app.app_context():
        sent_at, status = send_email(
            "Subject",
            ["dest@example.com"],
            "Body",
        )

    assert status == "error"
    assert sent_at is None
