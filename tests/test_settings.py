import os
import sys
import pytest

from app import create_app, db
from app.models import Settings

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
