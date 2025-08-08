from smtplib import SMTPException

from app import db
from app.models import User, Roles, Settings


def make_admin(app, email):
    """Set the specified user as an admin."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        user.role = Roles.ADMIN
        db.session.commit()


def test_admin_view_access(client, app, login):
    """Admin user should access admin views while others get 403."""
    login(email="admin@example.com", password="pass")
    make_admin(app, "admin@example.com")
    resp = client.get("/admin/beneficjenci")
    assert resp.status_code == 200

    client.get("/logout")
    login(email="user@example.com", password="pass")
    resp = client.get("/admin/beneficjenci")
    assert resp.status_code == 403


def test_send_test_email_failure(monkeypatch, client, app, login):
    """Exception during email sending should be handled gracefully."""
    login(email="admin@example.com", password="pass")
    make_admin(app, "admin@example.com")
    with app.app_context():
        settings = Settings(mail_server="localhost", mail_port=25, admin_email="admin@example.com")
        db.session.add(settings)
        db.session.commit()

    def fail_send(msg):
        raise SMTPException("boom")

    monkeypatch.setattr("app.utils.mail.send", fail_send)
    resp = client.post(
        "/admin/ustawienia",
        data={
            "mail_server": "localhost",
            "mail_port": 25,
            "mail_username": "",
            "mail_password": "",
            "mail_use_tls": "",
            "mail_use_ssl": "",
            "admin_email": "admin@example.com",
            "sender_name": "",
            "timezone": "UTC",
            "send_test": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Nie udało się wysłać testowego emaila." in resp.get_data(as_text=True)
