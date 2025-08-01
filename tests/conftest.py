"""Common pytest fixtures used across test modules."""

import os
import sys
import pytest
from app import create_app


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
