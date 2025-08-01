from datetime import date, time
import os

from app import db
from app.models import User, Beneficjent, Zajecia


def create_user(app):
    with app.app_context():
        user = User(full_name='tester', email='tester@example.com')
        user.set_password('secret')
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, username='tester', password='secret'):
    return client.post('/login', data={'full_name': username, 'password': password}, follow_redirects=True)


def test_beneficjent_crud(app, client):
    create_user(app)
    login(client)

    # Add
    response = client.post(
        '/beneficjenci/nowy',
        data={'imie': 'Jan Kowalski', 'wojewodztwo': 'Mazowieckie'},
        follow_redirects=True,
    )
    assert 'Beneficjent dodany' in response.get_data(as_text=True)
    with app.app_context():
        benef = Beneficjent.query.filter_by(imie='Jan Kowalski').first()
        assert benef is not None
        benef_id = benef.id

    # Edit
    response = client.post(
        f'/beneficjenci/{benef_id}/edytuj',
        data={'imie': 'Jan Nowak', 'wojewodztwo': 'Slaskie'},
        follow_redirects=True,
    )
    assert 'Beneficjent zaktualizowany' in response.get_data(as_text=True)
    with app.app_context():
        benef = db.session.get(Beneficjent, benef_id)
        assert benef.imie == 'Jan Nowak'
        assert benef.wojewodztwo == 'Slaskie'

    # Delete
    response = client.post(
        f'/beneficjenci/{benef_id}/usun',
        data={'submit': '1'},
        follow_redirects=True,
    )
    assert 'Beneficjent usunięty' in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Beneficjent, benef_id) is None


def test_create_session(app, client):
    user_id = create_user(app)
    login(client)
    with app.app_context():
        benef = Beneficjent(imie='Anna', wojewodztwo='Pomorskie', user_id=user_id)
        db.session.add(benef)
        db.session.commit()
        b_id = benef.id

    response = client.post('/zajecia/nowe', data={
        'data': '2023-01-01',
        'godzina_od': '10:00',
        'godzina_do': '11:00',
        'beneficjenci': [str(b_id)]
    }, follow_redirects=True)
    assert 'Zajęcia zapisane' in response.get_data(as_text=True)
    with app.app_context():
        zajecia = Zajecia.query.filter_by(user_id=user_id).first()
        assert zajecia is not None
        assert len(zajecia.beneficjenci) == 1


def test_pdf_generation(app, client):
    user_id = create_user(app)
    login(client)
    with app.app_context():
        benef = Beneficjent(imie='Piotr', wojewodztwo='Lubelskie', user_id=user_id)
        db.session.add(benef)
        zajecia = Zajecia(
            data=date(2023, 1, 2),
            godzina_od=time(9, 0),
            godzina_do=time(10, 0),
            specjalista='tester',
            user_id=user_id
        )
        zajecia.beneficjenci.append(benef)
        db.session.add(zajecia)
        db.session.commit()
        z_id = zajecia.id

    response = client.get(f'/zajecia/{z_id}/pdf')
    assert response.status_code == 200
    assert 'application/pdf' in response.headers.get('Content-Type', '')
    assert response.headers.get('Content-Disposition', '').startswith('attachment')

    pdf_path = os.path.join(app.root_path, 'static', 'pdf', f'zajecia_{z_id}.pdf')
    # the generated PDF should be removed after the response is sent
    assert not os.path.exists(pdf_path)
