import sys
from smtplib import SMTPException

from app import create_app, db, mail
from app.models import Settings, User, Roles
from flask_mail import Message
from tests.conftest import build_test_config, dispose_app


def make_app(monkeypatch, db_path):
    sys.modules.pop("app.routes", None)
    import app as app_package  # noqa: F401
    if hasattr(app_package, "routes"):
        delattr(app_package, "routes")

    return create_app(build_test_config(db_path))


def create_admin(app, admin_email=None, sender_name=None):
    with app.app_context():
        admin = User(full_name='admin', email='admin@example.com', role=Roles.ADMIN)
        admin.set_password('pass')
        admin.confirmed = True
        db.session.add(admin)
        s = Settings(
            mail_server='localhost',
            mail_port=25,
            mail_use_tls=False,
            mail_use_ssl=False,
            admin_email=admin_email,
            mail_sender_name=sender_name,
        )
        db.session.add(s)
        db.session.commit()


def login(client):
    return client.post(
        '/login',
        data={'email': 'admin@example.com', 'password': 'pass'},
        follow_redirects=True,
    )


def test_fallback_to_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MAIL_SERVER", "envhost")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("MAIL_USERNAME", "envuser")
    monkeypatch.setenv("MAIL_PASSWORD", "envpass")
    monkeypatch.setenv("TIMEZONE", "UTC")
    app = make_app(monkeypatch, tmp_path / "konsultacje.db")
    with app.app_context():
        assert Settings.query.first() is None
        assert app.config["MAIL_SERVER"] == "envhost"
        assert app.config["MAIL_PORT"] == 2525
        assert app.config["MAIL_USERNAME"] == "envuser"
        assert app.config["TIMEZONE"] == "UTC"
    dispose_app(app)


def test_settings_override_and_default(monkeypatch, tmp_path):
    db_path = tmp_path / "konsultacje.db"
    monkeypatch.setenv("MAIL_SERVER", "envhost")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("MAIL_USERNAME", "envuser")
    monkeypatch.setenv("MAIL_PASSWORD", "envpass")
    monkeypatch.setenv("TIMEZONE", "UTC")
    app = make_app(monkeypatch, db_path)
    with app.app_context():
        s = Settings(mail_server="dbhost", mail_port=None, mail_username=None)
        db.session.add(s)
        db.session.commit()
    dispose_app(app)
    app2 = make_app(monkeypatch, db_path)
    with app2.app_context():
        assert app2.config["MAIL_SERVER"] == "dbhost"
        assert app2.config["MAIL_PORT"] == 2525
        assert app2.config["MAIL_USERNAME"] == "envuser"
        assert app2.config["TIMEZONE"] == "UTC"
    dispose_app(app2)


def test_admin_email_overrides_env(monkeypatch, tmp_path):
    db_path = tmp_path / "konsultacje.db"
    monkeypatch.setenv("ADMIN_EMAIL", "env@example.com")
    app = make_app(monkeypatch, db_path)
    with app.app_context():
        s = Settings(admin_email="db@example.com")
        db.session.add(s)
        db.session.commit()
    dispose_app(app)
    app2 = make_app(monkeypatch, db_path)
    with app2.app_context():
        assert app2.config["MAIL_DEFAULT_SENDER"] == ("", "db@example.com")
    dispose_app(app2)


def test_sender_name_applied(monkeypatch, tmp_path):
    db_path = tmp_path / "konsultacje.db"
    app = make_app(monkeypatch, db_path)
    with app.app_context():
        s = Settings(admin_email="admin@example.com", mail_sender_name="Konsultacje")
        db.session.add(s)
        db.session.commit()
    dispose_app(app)
    app2 = make_app(monkeypatch, db_path)
    with app2.app_context():
        assert app2.config["MAIL_DEFAULT_SENDER"] == ("Konsultacje", "admin@example.com")
    dispose_app(app2)


def test_send_test_email_success(monkeypatch, tmp_path):
    app = make_app(monkeypatch, tmp_path / "konsultacje.db")
    create_admin(app, admin_email="stored@example.com")
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
            "timezone": "UTC",
            "send_test": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert len(sent) == 1
    assert sent[0].recipients == ["stored@example.com"]
    assert "Testowy email wysłany." in resp.get_data(as_text=True)
    dispose_app(app)


def test_send_test_email_failure(monkeypatch, tmp_path):
    app = make_app(monkeypatch, tmp_path / "konsultacje.db")
    create_admin(app, admin_email="stored@example.com")

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
            "timezone": "UTC",
            "send_test": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Nie udało się wysłać testowego emaila." in text
    dispose_app(app)


def test_smtp_host_updated_immediately(monkeypatch, tmp_path):
    app = make_app(monkeypatch, tmp_path / "konsultacje.db")
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
            "timezone": "UTC",
            "submit": "1",
        },
        follow_redirects=True,
    )

    hosts.clear()
    with app.app_context():
        mail.send(Message("after", sender="admin@example.com", recipients=["a@example.com"]))

    assert hosts[-1] == "newhost"
    dispose_app(app)
