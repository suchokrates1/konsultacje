"""Tests for authentication and password reset flows."""

import os
import re
import pytest
from smtplib import SMTPException

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
        assert admin.confirmed

    # create_app called again should not alter admin confirmation status
    app2 = create_app(config)
    with app2.app_context():
        admin = User.query.filter_by(full_name='admin').first()
        assert admin is not None
        assert admin.confirmed


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

    with app.app_context():
        user = User.query.filter_by(full_name='alice').first()
        user.confirmed = True
        db.session.commit()

    response = client.post('/login', data={
        'full_name': 'alice',
        'password': 'password',
        'remember_me': 'y',
    }, follow_redirects=True)
    assert b'Nowe zaj\xc4\x99cia' in response.data
    assert client.get_cookie('remember_token') is not None


def test_register_duplicate_email(client, app):
    """Registering with an existing email should show an error message."""
    # first registration
    client.post(
        '/register',
        data={
            'full_name': 'user1',
            'email': 'duplicate@example.com',
            'password': 'secret',
            'confirm': 'secret',
        },
        follow_redirects=True,
    )

    response = client.post(
        '/register',
        data={
            'full_name': 'user2',
            'email': 'duplicate@example.com',
            'password': 'secret',
            'confirm': 'secret',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert (
        'Użytkownik z tym adresem email już istnieje.'
        in response.get_data(as_text=True)
    )


def test_register_email_failure(monkeypatch, client, app):
    """Registration succeeds even if sending admin email fails."""
    monkeypatch.setenv('ADMIN_EMAIL', 'admin@example.com')

    def fail_send(msg):
        raise SMTPException('tls not supported')

    monkeypatch.setattr('app.routes.mail.send', fail_send)

    response = client.post(
        '/register',
        data={
            'full_name': 'fail',
            'email': 'fail@example.com',
            'password': 'secret',
            'confirm': 'secret',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert (
        'Rejestracja zakończona sukcesem. Poczekaj na potwierdzenie przez administratora.'
        in text
    )
    assert 'Nie udało się wysłać powiadomienia do administratora.' in text
    with app.app_context():
        assert User.query.filter_by(full_name='fail').first() is not None


def test_password_reset_flow(monkeypatch, app):
    """Test the full password reset process."""
    with app.app_context():
        user = User(full_name='bob', email='bob@example.com')
        user.set_password('oldpass')
        user.confirmed = True
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
    assert b'Nowe zaj\xc4\x99cia' in response.data


def test_unconfirmed_user_cannot_login(app):
    """Ensure unconfirmed users are prevented from logging in."""
    with app.app_context():
        user = User(full_name='unc', email='unc@example.com')
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    resp = client.post(
        '/login',
        data={'full_name': 'unc', 'password': 'pass'},
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert 'Twoje konto nie zostało jeszcze potwierdzone.' in text
    assert 'Nieprawidłowe dane logowania.' not in text
    assert 'Nowe zajęcia' not in text
