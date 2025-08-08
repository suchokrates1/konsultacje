"""Tests verifying access control based on user roles."""

from app import db
from app.models import User, Beneficjent, Roles


def create_users(app):
    """Create admin and instructor accounts with sample beneficiaries."""
    with app.app_context():
        admin = User(
            full_name='admin',
            email='admin@example.com',
            role=Roles.ADMIN,
        )
        admin.set_password('pass')
        admin.confirmed = True
        inst1 = User(full_name='inst1', email='i1@example.com')
        inst1.set_password('pass')
        inst1.confirmed = True
        inst2 = User(full_name='inst2', email='i2@example.com')
        inst2.set_password('pass')
        inst2.confirmed = True
        db.session.add_all([admin, inst1, inst2])
        db.session.commit()
        b1 = Beneficjent(
            imie='Ben1', wojewodztwo='Maz', user_id=inst1.id
        )
        b2 = Beneficjent(
            imie='Ben2', wojewodztwo='Maz', user_id=inst2.id
        )
        db.session.add_all([b1, b2])
        db.session.commit()
        return admin.id, inst1.id, inst2.id


def login(client, username):
    """Authenticate a test user and return the response."""

    email_map = {
        'admin': 'admin@example.com',
        'inst1': 'i1@example.com',
        'inst2': 'i2@example.com',
    }
    return client.post(
        '/login',
        data={'email': email_map.get(username, f'{username}@example.com'), 'password': 'pass'},
        follow_redirects=True,
    )


def test_admin_access(app):
    """Admin should be able to view all beneficiaries and users."""
    admin_id, inst1_id, inst2_id = create_users(app)
    client = app.test_client()
    login(client, 'admin')
    resp = client.get('/admin/beneficjenci')
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert 'Ben1' in text and 'Ben2' in text

    resp = client.get('/admin/uzytkownicy')
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert 'inst1' in text
    assert 'Instruktorzy' in text and 'Administratorzy' in text


def test_instructor_cannot_access_admin(app):
    """Non-admin users must receive 403 when accessing admin pages."""
    admin_id, inst1_id, inst2_id = create_users(app)
    client = app.test_client()
    login(client, 'inst1')
    resp = client.get('/admin/beneficjenci')
    assert resp.status_code == 403


def test_instructor_sees_own_beneficiaries(app):
    """Instructor pages show only beneficiaries belonging to that user."""
    admin_id, inst1_id, inst2_id = create_users(app)
    client = app.test_client()
    login(client, 'inst1')
    resp = client.get('/beneficjenci')
    text = resp.get_data(as_text=True)
    assert 'Ben1' in text
    assert 'Ben2' not in text


def test_promote_instructor(app):
    """Admin can promote an instructor who then gains admin access."""
    admin_id, inst1_id, inst2_id = create_users(app)
    client = app.test_client()
    login(client, 'admin')
    resp = client.post(
        f'/admin/uzytkownicy/{inst1_id}/promote',
        data={'submit': '1'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        user = db.session.get(User, inst1_id)
        assert user.role == Roles.ADMIN
    # Instructor should now have admin rights
    login(client, 'inst1')
    resp = client.get('/admin/uzytkownicy')
    assert resp.status_code == 200


def test_confirm_instructor(app):
    """Admin can confirm an instructor so they can log in."""
    admin_id, inst1_id, inst2_id = create_users(app)
    with app.app_context():
        new_user = User(full_name='newbie', email='newbie@example.com')
        new_user.set_password('pass')
        db.session.add(new_user)
        db.session.commit()
        new_id = new_user.id

    client = app.test_client()
    # Unconfirmed user should not be able to log in
    resp = client.post(
        '/login',
        data={'email': 'newbie@example.com', 'password': 'pass'},
        follow_redirects=True,
    )
    assert 'Twoje konto nie zostało jeszcze potwierdzone.' in resp.get_data(as_text=True)

    login(client, 'admin')
    # Page should show confirmation button for the new user
    resp = client.get('/admin/uzytkownicy')
    assert 'Potwierdź rejestrację' in resp.get_data(as_text=True)

    resp = client.post(
        f'/admin/uzytkownicy/{new_id}/confirm',
        data={'submit': '1'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        confirmed = db.session.get(User, new_id)
        assert confirmed.confirmed

    # User should now be able to log in
    resp = client.post(
        '/login',
        data={'email': 'newbie@example.com', 'password': 'pass'},
        follow_redirects=True,
    )
    assert 'Nowe zajęcia' in resp.get_data(as_text=True)
