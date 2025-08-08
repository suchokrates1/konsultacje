"""Common pytest fixtures used across test modules."""

import os
import sys
import pytest
from app import create_app, db
from app.models import User


@pytest.fixture
def app(monkeypatch):
    """Create a new application instance for testing."""

    db_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "instance",
        "konsultacje.db",
    )
    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    # Reload routes so they register on a fresh app instance
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
    app = create_app(config)
    return app


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
