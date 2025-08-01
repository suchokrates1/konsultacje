"""Tests covering search functionality for beneficiaries and sessions."""

from datetime import date, time
from app import db
from app.models import User, Beneficjent, Zajecia


def setup_data(app):
    """Populate the database with sample data for searching."""

    with app.app_context():
        user = User(full_name="test", email="test@example.com")
        user.set_password("secret")
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        b1 = Beneficjent(imie="Alice", wojewodztwo="Maz", user_id=user.id)
        b2 = Beneficjent(imie="Bob", wojewodztwo="Slask", user_id=user.id)
        db.session.add_all([b1, b2])
        z1 = Zajecia(
            data=date(2023, 1, 1),
            godzina_od=time(8, 0),
            godzina_do=time(9, 0),
            specjalista="Spec1",
            user_id=user.id,
        )
        z1.beneficjenci.append(b1)
        z2 = Zajecia(
            data=date(2023, 1, 2),
            godzina_od=time(9, 0),
            godzina_do=time(10, 0),
            specjalista="Spec2",
            user_id=user.id,
        )
        z2.beneficjenci.append(b2)
        db.session.add_all([z1, z2])
        db.session.commit()
        return user.id


def login(client):
    """Log the test user in and return the response."""

    return client.post(
        "/login",
        data={"email": "test@example.com", "password": "secret"},
        follow_redirects=True,
    )


def test_filter_beneficjenci(app, client):
    """Ensure the beneficiary list can be filtered by name."""
    setup_data(app)
    login(client)
    resp = client.get("/beneficjenci?q=Ali")
    text = resp.get_data(as_text=True)
    assert "Alice" in text
    assert "Bob" not in text


def test_filter_zajecia(app, client):
    """Ensure the session list can be filtered by date."""
    setup_data(app)
    login(client)
    resp = client.get("/zajecia?q=2023-01-02")
    text = resp.get_data(as_text=True)
    assert "02.01.2023" in text
    assert "01.01.2023" not in text
