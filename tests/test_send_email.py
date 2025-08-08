from smtplib import SMTPException

from app.utils import send_email


def test_send_email_sends_message(monkeypatch, app):
    messages = []

    def fake_send(msg):
        messages.append(msg)

    monkeypatch.setattr("app.utils.mail.send", fake_send)

    with app.app_context():
        sent_at, status = send_email(
            "Hello",
            ["dest@example.com"],
            "Body",
            attachments=[("test.txt", "text/plain", b"data")],
        )

    assert status == "sent"
    assert sent_at is not None
    assert messages
    msg = messages[0]
    assert msg.subject == "Hello"
    assert msg.recipients == ["dest@example.com"]
    assert msg.body == "Body"
    assert len(msg.attachments) == 1
    attachment = msg.attachments[0]
    assert attachment.filename == "test.txt"
    assert attachment.content_type == "text/plain"


def test_send_email_handles_smtp_exception(monkeypatch, app):
    def fake_send(msg):
        raise SMTPException("fail")

    monkeypatch.setattr("app.utils.mail.send", fake_send)

    with app.app_context():
        sent_at, status = send_email(
            "Hello",
            ["dest@example.com"],
            "Body",
        )

    assert status == "error"
    assert sent_at is None
