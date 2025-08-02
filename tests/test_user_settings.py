import pytest
from app import db
from app.models import User


def create_user(app):
    with app.app_context():
        user = User(full_name='change', email='c@example.com')
        user.set_password('old')
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client):
    return client.post(
        '/login',
        data={'full_name': 'change', 'password': 'old'},
        follow_redirects=True,
    )


def test_settings_requires_login(client):
    resp = client.get('/settings', follow_redirects=True)
    assert resp.request.path == '/login'


def test_settings_password_change_success(app, client):
    create_user(app)
    login(client)
    resp = client.post(
        '/settings',
        data={
            'email': 'c@example.com',
            'full_name': 'change',
            'default_duration': 90,
            'old_password': 'old',
            'new_password': 'new',
            'confirm': 'new',
        },
        follow_redirects=True,
    )
    assert 'Ustawienia zapisane' in resp.get_data(as_text=True)
    with app.app_context():
        user = User.query.filter_by(full_name='change').first()
        assert user.check_password('new')


def test_settings_wrong_old_password(app, client):
    create_user(app)
    login(client)
    resp = client.post(
        '/settings',
        data={
            'email': 'c@example.com',
            'full_name': 'change',
            'default_duration': 90,
            'old_password': 'bad',
            'new_password': 'new',
            'confirm': 'new',
        },
        follow_redirects=True,
    )
    assert 'Nieprawidłowe aktualne hasło' in resp.get_data(as_text=True)


def test_settings_form_prefilled_with_user_data(app, client):
    """GET /settings should render form fields populated with current user data."""
    create_user(app)
    login(client)
    resp = client.get('/settings')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'value="c@example.com"' in html
    assert 'value="change"' in html
    assert 'value="90"' in html


def test_settings_missing_required_fields_shows_errors(app, client):
    """Submitting without required fields should re-render form and keep data unchanged."""
    create_user(app)
    login(client)
    resp = client.post(
        '/settings',
        data={'email': '', 'full_name': '', 'default_duration': ''},
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Ustawienia użytkownika' in html
    with app.app_context():
        user = User.query.filter_by(full_name='change').first()
        assert user.email == 'c@example.com'


def test_custom_error_pages(app, client):
    create_user(app)

    @app.route('/cause_error')
    def cause_error():
        raise RuntimeError('boom')

    app.config['PROPAGATE_EXCEPTIONS'] = False

    resp = client.get('/nonexistent')
    assert resp.status_code == 404
    assert 'Nie znaleziono strony' in resp.get_data(as_text=True)

    resp = client.get('/cause_error')
    assert resp.status_code == 500
    assert 'Wystąpił błąd serwera' in resp.get_data(as_text=True)

