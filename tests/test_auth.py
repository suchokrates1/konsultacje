"""Tests for authentication and password reset flows."""

import os
import re
import pytest

from app import create_app, db
from app.models import User

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "instance",
    "konsultacje.db",
)


def setup_database():
    """Remove the test database if it exists and recreate directories."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@pytest.fixture
def app(monkeypatch):
    """Provide a configured Flask app for tests."""

    setup_database()
    # Reload routes so they register on the fresh app instance
    import sys
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
    """Return a test client for the provided app."""

    return app.test_client()


def test_admin_created_from_env(monkeypatch):
    """Verify that an admin user is created from environment variables."""
    setup_database()
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'adminpass')
    monkeypatch.setenv('ADMIN_EMAIL', 'admin@example.com')
    config = {
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
    }
    app = create_app(config)
    with app.app_context():
        admin = User.query.filter_by(full_name='admin').first()
        assert admin is not None
        assert admin.email == 'admin@example.com'
        assert admin.check_password('adminpass')
        assert admin.role == 'admin'


def test_register_and_login_remember_me(client, app):
    """Register a user and log in with the remember me option."""
    response = client.post(
        '/register',
        data={
            'full_name': 'alice',
            'email': 'alice@example.com',
            'password': 'password',
            'confirm': 'password',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert User.query.filter_by(full_name='alice').first() is not None

    response = client.post('/login', data={
        'full_name': 'alice',
        'password': 'password',
        'remember_me': 'y',
    }, follow_redirects=True)
    assert b'Witaj' in response.data
    assert client.get_cookie('remember_token') is not None


def test_register_duplicate_email(client, app):
    """Registering with an existing email should show an error message."""
    # first registration
    client.post(
        '/register',
        data={
            'full_name': 'user1',
            'email': 'duplicate@example.com',
            'password': 'secret123',
            'confirm': 'secret123',
        },
        follow_redirects=True,
    )

    response = client.post(
        '/register',
        data={
            'full_name': 'user2',
            'email': 'duplicate@example.com',
            'password': 'secret123',
            'confirm': 'secret123',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert (
        'Użytkownik z tym adresem email już istnieje.'
        in response.get_data(as_text=True)
    )


def test_register_duplicate_username(client, app):
    client.post(
        '/register',
        data={
            'username': 'sameuser',
            'email': 'first@example.com',
            'password': 'secret123',
            'confirm': 'secret123',
        },
        follow_redirects=True,
    )

    response = client.post(
        '/register',
        data={
            'username': 'sameuser',
            'email': 'other@example.com',
            'password': 'secret123',
            'confirm': 'secret123',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert 'Nazwa użytkownika jest już zajęta.' in response.get_data(as_text=True)


def test_register_short_password(client, app):
    response = client.post(
        '/register',
        data={
            'username': 'weak',
            'email': 'weak@example.com',
            'password': 'short',
            'confirm': 'short',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert 'Hasło musi mieć co najmniej 8 znaków.' in response.get_data(as_text=True)


def test_password_reset_flow(monkeypatch, app):
    """Test the full password reset process."""
    with app.app_context():
        user = User(full_name='bob', email='bob@example.com')
        user.set_password('oldpass')
        db.session.add(user)
        db.session.commit()

    sent = []

    def fake_send(msg):
        sent.append(msg)

    monkeypatch.setattr('app.routes.mail.send', fake_send)
    client = app.test_client()

    response = client.post(
        '/reset_password_request',
        data={'email': 'bob@example.com'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert response.request.path == '/login'
    assert len(sent) == 1

    m = re.search(r'/reset_password/(.*)', sent[0].body)
    assert m, sent[0].body
    token = m.group(1)

    response = client.post(
        f'/reset_password/{token}',
        data={'password': 'newpass', 'confirm': 'newpass'},
        follow_redirects=True,
    )
    assert response.request.path == '/login'

    response = client.post(
        '/login',
        data={'full_name': 'bob', 'password': 'newpass'},
        follow_redirects=True,
    )
    assert b'Witaj' in response.data
