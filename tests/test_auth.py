import os
import re
import pytest

from app import create_app, db
from app.models import User

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'instance', 'konsultacje.db')


def setup_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@pytest.fixture
def app(monkeypatch):
    setup_database()
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    # Reload routes so they register on the fresh app instance
    import sys
    sys.modules.pop('app.routes', None)
    import app as app_package
    if hasattr(app_package, 'routes'):
        delattr(app_package, 'routes')
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, MAIL_SUPPRESS_SEND=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_admin_created_from_env(monkeypatch):
    setup_database()
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'adminpass')
    monkeypatch.setenv('ADMIN_EMAIL', 'admin@example.com')
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.email == 'admin@example.com'
        assert admin.check_password('adminpass')


def test_register_and_login_remember_me(client, app):
    response = client.post(
        '/register',
        data={
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'password',
            'confirm': 'password',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert User.query.filter_by(username='alice').first() is not None

    response = client.post('/login', data={
        'username': 'alice',
        'password': 'password',
        'remember_me': 'y',
    }, follow_redirects=True)
    assert b'Witaj' in response.data
    assert client.get_cookie('remember_token') is not None


def test_password_reset_flow(monkeypatch, app):
    with app.app_context():
        user = User(username='bob', email='bob@example.com')
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

    response = client.post('/login', data={'username': 'bob', 'password': 'newpass'}, follow_redirects=True)
    assert b'Witaj' in response.data
