import os
import sys
import pytest
from smtplib import SMTPException

from app import create_app, db, mail
from app.models import Settings, User, Roles
from flask_mail import Message

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "instance",
    "konsultacje.db",
)


def setup_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def make_app(monkeypatch):
    sys.modules.pop("app.routes", None)
    import app as app_package  # noqa: F401
    if hasattr(app_package, "routes"):
        delattr(app_package, "routes")

    config = {
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True,
        "SECRET_KEY": "test-secret",
    }
    return create_app(config)


def create_admin(app):
    with app.app_context():
        admin = User(full_name='admin', email='admin@example.com', role=Roles.ADMIN)
        admin.set_password('pass')
        db.session.add(admin)
        s = Settings(mail_server='localhost', mail_port=25,
                     mail_use_tls=False, mail_use_ssl=False)
        db.session.add(s)
        db.session.commit()


def login(client):
    return client.post(
        '/login',
        data={'full_name': 'admin', 'password': 'pass'},
        follow_redirects=True,
    )


def test_fallback_to_env(monkeypatch):
    setup_database()
    monkeypatch.setenv("MAIL_SERVER", "envhost")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("MAIL_USERNAME", "envuser")
    monkeypatch.setenv("MAIL_PASSWORD", "envpass")
    monkeypatch.setenv("TIMEZONE", "UTC")
    app = make_app(monkeypatch)
    with app.app_context():
        assert Settings.query.first() is None
        assert app.config["MAIL_SERVER"] == "envhost"
        assert app.config["MAIL_PORT"] == 2525
        assert app.config["MAIL_USERNAME"] == "envuser"
        assert app.config["TIMEZONE"] == "UTC"


def test_settings_override_and_default(monkeypatch):
    setup_database()
    monkeypatch.setenv("MAIL_SERVER", "envhost")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("MAIL_USERNAME", "envuser")
    monkeypatch.setenv("MAIL_PASSWORD", "envpass")
    monkeypatch.setenv("TIMEZONE", "UTC")
    app = make_app(monkeypatch)
    with app.app_context():
        s = Settings(mail_server="dbhost", mail_port=None, mail_username=None)
        db.session.add(s)
        db.session.commit()
    app2 = make_app(monkeypatch)
    with app2.app_context():
        assert app2.config["MAIL_SERVER"] == "dbhost"
        assert app2.config["MAIL_PORT"] == 2525
        assert app2.config["MAIL_USERNAME"] == "envuser"
        assert app2.config["TIMEZONE"] == "UTC"


def test_send_test_email_success(monkeypatch):
    setup_database()
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    app = make_app(monkeypatch)
    create_admin(app)
    sent = []

    def fake_send(msg):
        sent.append(msg)

    monkeypatch.setattr("app.routes.mail.send", fake_send)
    client = app.test_client()
    login(client)
    resp = client.post(
        "/admin/ustawienia",
        data={
            "mail_server": "localhost",
            "mail_port": 25,
            "mail_username": "",
            "mail_password": "",
            "mail_use_tls": "y",
            "mail_use_ssl": "",
            "timezone": "",
            "send_test": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert len(sent) == 1
    assert "Testowy email wysłany." in resp.get_data(as_text=True)


def test_send_test_email_failure(monkeypatch):
    setup_database()
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    app = make_app(monkeypatch)
    create_admin(app)

    def fail_send(msg):
        raise SMTPException("boom")

    monkeypatch.setattr("app.routes.mail.send", fail_send)
    client = app.test_client()
    login(client)
    resp = client.post(
        "/admin/ustawienia",
        data={
            "mail_server": "localhost",
            "mail_port": 25,
            "mail_username": "",
            "mail_password": "",
            "mail_use_tls": "y",
            "mail_use_ssl": "",
            "timezone": "",
            "send_test": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Nie udało się wysłać testowego emaila." in text


def test_smtp_host_updated_immediately(monkeypatch):
    setup_database()
    app = make_app(monkeypatch)
    create_admin(app)
    app.config["MAIL_SUPPRESS_SEND"] = False
    mail.init_app(app)

    hosts = []

    class DummySMTP:
        def __init__(self, host="", port=0, *args, **kwargs):
            hosts.append(host)

        def sendmail(self, *args, **kwargs):
            pass

        def login(self, *args, **kwargs):
            pass

        def quit(self):
            pass

        def starttls(self, *args, **kwargs):
            pass

        def set_debuglevel(self, *args, **kwargs):
            pass

    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    monkeypatch.setattr("smtplib.SMTP_SSL", DummySMTP)

    with app.app_context():
        mail.send(Message("before", sender="admin@example.com", recipients=["a@example.com"]))

    assert hosts[-1] == "localhost"

    client = app.test_client()
    login(client)
    client.post(
        "/admin/ustawienia",
        data={
            "mail_server": "newhost",
            "mail_port": 25,
            "mail_username": "",
            "mail_password": "",
            "mail_use_tls": "",
            "mail_use_ssl": "",
            "timezone": "",
            "submit": "1",
        },
        follow_redirects=True,
    )

    hosts.clear()
    with app.app_context():
        mail.send(Message("after", sender="admin@example.com", recipients=["a@example.com"]))

    assert hosts[-1] == "newhost"
