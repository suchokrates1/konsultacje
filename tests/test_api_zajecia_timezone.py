import pytest
from datetime import date, time, datetime

from app import db
from app.models import User, Beneficjent, Zajecia


def create_user(app, name="user", email=None):
    with app.app_context():
        user = User(full_name=name, email=email or f"{name}@example.com")
        user.set_password("secret")
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, name="user", email=None):
    return client.post(
        "/login",
        data={"email": email or f"{name}@example.com", "password": "secret"},
        follow_redirects=True,
    )


def create_session(app, user_id):
    with app.app_context():
        benef = Beneficjent(
            imie="Benef",
            wojewodztwo="Mazowieckie",
            user_id=user_id,
        )
        db.session.add(benef)
        today = date.today()
        zaj = Zajecia(
            data=today,
            godzina_od=time(9, 0),
            godzina_do=time(10, 0),
            specjalista="spec",
            user_id=user_id,
        )
        zaj.beneficjenci.append(benef)
        db.session.add(zaj)
        db.session.commit()
        return zaj.id, benef.id


def test_api_zajecia_returns_timezone(app, client):
    user_id = create_user(app)
    login(client)
    create_session(app, user_id)

    resp = client.get("/api/zajecia")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    start = datetime.fromisoformat(data[0]["start"])
    end = datetime.fromisoformat(data[0]["end"])
    assert start.tzinfo is not None
    assert end.tzinfo is not None
