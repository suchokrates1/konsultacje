import re
from datetime import date, time

from app import db
from app.models import User, Beneficjent, Zajecia


def create_user(app):
    with app.app_context():
        user = User(full_name='field', email='field@example.com')
        user.set_password('secret')
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client):
    return client.post(
        '/login',
        data={'full_name': 'field', 'password': 'secret'},
        follow_redirects=True,
    )


def add_beneficjent(app, user_id, name='Jan'):
    with app.app_context():
        benef = Beneficjent(imie=name, wojewodztwo='Mazowieckie', user_id=user_id)
        db.session.add(benef)
        db.session.commit()
        return benef.id


def test_beneficjent_field_renders_single_choice(app, client):
    user_id = create_user(app)
    add_beneficjent(app, user_id)
    login(client)
    resp = client.get('/zajecia/nowe')
    html = resp.get_data(as_text=True)
    match = re.search(r'<select[^>]*name="beneficjenci"[^>]*>', html)
    assert match is not None
    assert 'multiple' not in match.group(0)


def test_beneficjent_field_requires_selection(app, client):
    user_id = create_user(app)
    add_beneficjent(app, user_id)
    login(client)
    resp = client.post(
        '/zajecia/nowe',
        data={
            'data': '2023-01-01',
            'godzina_od': '10:00',
            'godzina_do': '11:00',
        },
        follow_redirects=True,
    )
    assert resp.request.path == '/zajecia/nowe'
    with app.app_context():
        assert Zajecia.query.count() == 0
