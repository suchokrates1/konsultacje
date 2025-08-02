import io
from datetime import date, time
from pathlib import Path

from docx import Document
from app import db
from app.models import User, Beneficjent, Zajecia


def create_user(app, name='doc', email=None):
    with app.app_context():
        user = User(full_name=name, email=email or f'{name}@example.com')
        user.set_password('secret')
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, name='doc'):
    return client.post(
        '/login',
        data={'full_name': name, 'password': 'secret'},
        follow_redirects=True,
    )


def create_session(app, user_id):
    with app.app_context():
        benef = Beneficjent(imie='Benef', wojewodztwo='Mazowieckie', user_id=user_id)
        db.session.add(benef)
        zaj = Zajecia(
            data=date(2023, 1, 1),
            godzina_od=time(9, 0),
            godzina_do=time(10, 0),
            specjalista='spec',
            user_id=user_id,
        )
        zaj.beneficjenci.append(benef)
        db.session.add(zaj)
        db.session.commit()
        return zaj.id


def test_docx_route_returns_valid_file(app, client):
    user_id = create_user(app)
    login(client)
    z_id = create_session(app, user_id)
    resp = client.get(f'/zajecia/{z_id}/docx')
    assert resp.status_code == 200
    assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in resp.headers.get('Content-Type', '')
    Document(io.BytesIO(resp.data))


def test_docx_route_creates_no_pdf(app, client, monkeypatch):
    """Generated DOCX download should not leave PDF artifacts on disk."""
    user_id = create_user(app)
    login(client)
    z_id = create_session(app, user_id)

    import app.routes as routes
    import app.docx_generator as docx_module

    called = {"val": False}

    def spy(zajecia, beneficjenci, output_path):
        called["val"] = True
        return docx_module.generate_docx(zajecia, beneficjenci, output_path)

    monkeypatch.setattr(routes, "generate_docx", spy)

    resp = client.get(f"/zajecia/{z_id}/docx")
    assert resp.status_code == 200
    Document(io.BytesIO(resp.data))
    assert called["val"]

    output_dir = Path(app.root_path) / "static" / "docx"
    assert not list(output_dir.glob("*.pdf"))


def test_docx_route_requires_ownership(app, client):
    owner_id = create_user(app, name='owner', email='owner@example.com')
    z_id = create_session(app, owner_id)
    create_user(app, name='other', email='other@example.com')
    login(client, name='other')
    resp = client.get(f'/zajecia/{z_id}/docx')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/')


def test_docx_route_missing_session_returns_404(app, client):
    create_user(app)
    login(client)
    resp = client.get('/zajecia/999/docx')
    assert resp.status_code == 404
