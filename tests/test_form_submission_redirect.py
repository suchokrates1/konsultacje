from flask import url_for
from app import db
from app.models import Beneficjent, User, Roles


def test_zajecia_creation_redirect(client, app, login):
    """Posting valid data to /zajecia/nowe should redirect to session list."""
    login()
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        benef = Beneficjent(imie="Benef", wojewodztwo="Mazowieckie", user_id=user.id)
        db.session.add(benef)
        db.session.commit()
        benef_id = benef.id

    resp = client.post(
        "/zajecia/nowe",
        data={
            "data": "2023-01-01",
            "godzina_od": "09:00",
            "godzina_do": "10:00",
            "specjalista": "spec",
            "beneficjenci": benef_id,
            "save": "1",
        },
    )
    assert resp.status_code == 302
    with app.test_request_context():
        assert resp.headers["Location"] == url_for("sessions.lista_zajec")


def test_beneficjent_creation_redirect(client, app, login):
    """Posting valid data to /beneficjenci/nowy should redirect to beneficiary list."""
    login()
    resp = client.post(
        "/beneficjenci/nowy",
        data={
            "imie": "Benef",
            "wojewodztwo": "Mazowieckie",
            "submit": "1",
        },
    )
    assert resp.status_code == 302
    with app.test_request_context():
        assert resp.headers["Location"] == url_for("sessions.lista_beneficjentow")


def test_admin_settings_redirect(client, app, login):
    """Posting valid data to /admin/ustawienia should redirect back to settings page."""
    login(email="admin@example.com")
    with app.app_context():
        user = User.query.filter_by(email="admin@example.com").first()
        user.role = Roles.ADMIN
        db.session.commit()

    resp = client.post(
        "/admin/ustawienia",
        data={
            "mail_server": "localhost",
            "mail_port": 25,
            "mail_username": "",
            "mail_password": "",
            "mail_use_tls": "y",
            "mail_use_ssl": "",
            "admin_email": "admin@example.com",
            "sender_name": "",
            "timezone": "UTC",
            "submit": "1",
        },
    )
    assert resp.status_code == 302
    with app.test_request_context():
        assert resp.headers["Location"] == url_for("admin.admin_ustawienia")
