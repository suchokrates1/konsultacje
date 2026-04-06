"""Common pytest fixtures used across test modules."""

import sys
import pytest
from datetime import datetime, UTC
import flask_login.login_manager as login_manager
from app import create_app, db
from app.models import User


# Use timezone-aware datetimes in flask-login to avoid deprecation warnings
class _AwareDatetime(datetime):
    @classmethod
    def utcnow(cls):  # pragma: no cover - simple patch
        return datetime.now(UTC)


login_manager.datetime = _AwareDatetime


def build_test_config(db_path):
    return {
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path.as_posix()}",
    }


def dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def app(monkeypatch, tmp_path):
    """Create a new application instance for testing."""

    # Reload routes so they register on a fresh app instance
    sys.modules.pop("app.routes", None)
    import app as app_package  # noqa: F401
    if hasattr(app_package, "routes"):
        delattr(app_package, "routes")

    app = create_app(build_test_config(tmp_path / "konsultacje.db"))
    yield app
    dispose_app(app)


@pytest.fixture
def client(app):
    """Return a test client for the given application."""

    return app.test_client()


@pytest.fixture
def login(client, app):
    """Log in a test user."""

    def do_login(email="test@example.com", password="password"):
        with app.app_context():
            if not User.query.filter_by(email=email).first():
                user = User(full_name="Test", email=email)
                user.set_password(password)
                user.confirmed = True
                db.session.add(user)
                db.session.commit()
        return client.post("/login", data={"email": email, "password": password})

    return do_login


@pytest.fixture
def auth(login):
    """Provide authentication actions for tests."""

    class AuthActions:
        def login(self, email="test@example.com", password="password"):
            return login(email, password)

    return AuthActions()
