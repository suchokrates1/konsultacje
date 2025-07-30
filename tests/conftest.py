import os
import sys
import pytest
from app import create_app


@pytest.fixture
def app(monkeypatch):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'konsultacje.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')

    # Reload routes so they register on a fresh app instance
    sys.modules.pop('app.routes', None)
    import app as app_package  # noqa: F401
    if hasattr(app_package, 'routes'):
        delattr(app_package, 'routes')

    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'MAIL_SUPPRESS_SEND': True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()
