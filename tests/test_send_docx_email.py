from pathlib import Path

from app import db
from app.models import User, Beneficjent, Zajecia


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


def test_submit_send_dispatches_email_with_attachment(monkeypatch, app, client):
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
            'specjalista': 'spec',
            'beneficjenci': str(b_id),
            'submit_send': '1',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert messages
    msg = messages[0]
    assert msg.recipients == ['dest@example.com']
    assert len(msg.attachments) == 1
    assert msg.attachments[0].filename.endswith('.docx')

    output_dir = Path(app.root_path) / 'static' / 'docx'
    assert not (
        output_dir / 'Konsultacje z spec 2023-01-01 Ala.docx'
    ).exists()

    with app.app_context():
        zaj = Zajecia.query.one()
        assert zaj.doc_sent_at is not None
