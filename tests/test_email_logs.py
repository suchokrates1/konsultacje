from pathlib import Path

from app import db
from app.models import User, Beneficjent, SentEmail


def create_user(app):
    with app.app_context():
        user = User(
            full_name='sender',
            email='sender@example.com',
            document_recipient_email='dest@example.com',
        )
        user.set_password('secret')
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client):
    return client.post(
        '/login',
        data={'email': 'sender@example.com', 'password': 'secret'},
        follow_redirects=True,
    )


def test_email_log_and_resend(monkeypatch, app, client):
    user_id = create_user(app)
    login(client)
    with app.app_context():
        benef = Beneficjent(
            imie='Ala', wojewodztwo='Mazowieckie', user_id=user_id
        )
        db.session.add(benef)
        db.session.commit()
        b_id = benef.id

    messages = []

    def fake_send(msg):
        messages.append(msg)

    def fake_generate_docx(zajecia, beneficjenci, output_path):
        Path(output_path).write_bytes(b'dummy')

    monkeypatch.setattr('app.routes.mail.send', fake_send)
    monkeypatch.setattr('app.routes.generate_docx', fake_generate_docx)

    resp = client.post(
        '/zajecia/nowe',
        data={
            'data': '2023-01-01',
            'godzina_od': '10:00',
            'godzina_do': '11:00',
            'beneficjenci': str(b_id),
            'submit_send': '1',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert len(messages) == 1

    with app.app_context():
        log = SentEmail.query.one()
        assert log.recipient == 'dest@example.com'
        assert log.status == 'sent'
        first_sent_at = log.sent_at
        email_id = log.id

    resp = client.get('/emails')
    assert resp.status_code == 200
    assert b'dest@example.com' in resp.data

    resp = client.get(f'/emails/{email_id}/resend', follow_redirects=True)
    assert resp.status_code == 200
    assert len(messages) == 2

    with app.app_context():
        log = SentEmail.query.get(email_id)
        assert log.status == 'sent'
        assert log.sent_at != first_sent_at

