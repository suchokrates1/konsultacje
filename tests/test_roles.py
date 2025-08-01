import os
import pytest
from app import db
from app.models import User, Beneficjent, Zajecia


def create_users(app):
    with app.app_context():
        admin = User(full_name='admin', email='admin@example.com', role='admin')
        admin.set_password('pass')
        inst1 = User(full_name='inst1', email='i1@example.com')
        inst1.set_password('pass')
        inst2 = User(full_name='inst2', email='i2@example.com')
        inst2.set_password('pass')
        db.session.add_all([admin, inst1, inst2])
        db.session.commit()
        b1 = Beneficjent(imie='Ben1', wojewodztwo='Maz', user_id=inst1.id)
        b2 = Beneficjent(imie='Ben2', wojewodztwo='Maz', user_id=inst2.id)
        db.session.add_all([b1, b2])
        db.session.commit()
        return admin.id, inst1.id, inst2.id


def login(client, username):
    return client.post('/login', data={'full_name': username, 'password': 'pass'}, follow_redirects=True)


def test_admin_access(app):
    admin_id, inst1_id, inst2_id = create_users(app)
    client = app.test_client()
    login(client, 'admin')
    resp = client.get('/admin/beneficjenci')
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert 'Ben1' in text and 'Ben2' in text

    resp = client.get('/admin/instruktorzy')
    assert resp.status_code == 200
    assert 'inst1' in resp.get_data(as_text=True)


def test_instructor_cannot_access_admin(app):
    admin_id, inst1_id, inst2_id = create_users(app)
    client = app.test_client()
    login(client, 'inst1')
    resp = client.get('/admin/beneficjenci')
    assert resp.status_code == 403


def test_instructor_sees_own_beneficiaries(app):
    admin_id, inst1_id, inst2_id = create_users(app)
    client = app.test_client()
    login(client, 'inst1')
    resp = client.get('/beneficjenci')
    text = resp.get_data(as_text=True)
    assert 'Ben1' in text
    assert 'Ben2' not in text
