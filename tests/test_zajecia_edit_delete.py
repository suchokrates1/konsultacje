import pytest
from datetime import date, time

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
        zaj = Zajecia(
            data=date(2023, 1, 1),
            godzina_od=time(9, 0),
            godzina_do=time(10, 0),
            specjalista="spec",
            user_id=user_id,
        )
        zaj.beneficjenci.append(benef)
        db.session.add(zaj)
        db.session.commit()
        return zaj.id, benef.id


def test_session_list_shows_actions(app, client):
    user_id = create_user(app)
    login(client)
    z_id, _ = create_session(app, user_id)

    resp = client.get("/zajecia")
    text = resp.get_data(as_text=True)
    assert f"/zajecia/{z_id}/edytuj" in text
    assert f"/zajecia/{z_id}/usun" in text


def test_edit_session(app, client):
    user_id = create_user(app)
    login(client)
    z_id, b_id = create_session(app, user_id)

    resp = client.post(
        f"/zajecia/{z_id}/edytuj",
        data={
            "data": "2023-01-01",
            "godzina_od": "09:00",
            "godzina_do": "11:00",
            "specjalista": "spec2",
            "beneficjenci": b_id,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        zaj = db.session.get(Zajecia, z_id)
        assert zaj.godzina_do == time(11, 0)


def test_delete_session(app, client):
    user_id = create_user(app)
    login(client)
    z_id, _ = create_session(app, user_id)

    resp = client.post(
        f"/zajecia/{z_id}/usun",
        data={"submit": "1"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Zajecia, z_id) is None


def test_ajax_list_and_delete_session(app, client):
    user_id = create_user(app)
    login(client)
    z_id, _ = create_session(app, user_id)

    resp = client.get("/zajecia", headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert f"/zajecia/{z_id}/usun" in text

    resp = client.post(
        f"/zajecia/{z_id}/usun", data={"submit": "1"}, follow_redirects=True
    )
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Zajecia, z_id) is None


def test_cannot_edit_or_delete_foreign_session(app, client):
    owner_id = create_user(app, name="owner", email="owner@example.com")
    z_id, b_id = create_session(app, owner_id)
    create_user(app, name="other", email="other@example.com")
    login(client, name="other", email="other@example.com")

    resp = client.post(
        f"/zajecia/{z_id}/edytuj",
        data={
            "data": "2023-02-01",
            "godzina_od": "09:00",
            "godzina_do": "11:00",
            "beneficjenci": b_id,
        },
    )
    assert resp.status_code == 302
    with app.app_context():
        zaj = db.session.get(Zajecia, z_id)
        assert zaj.godzina_do == time(10, 0)

    resp = client.post(f"/zajecia/{z_id}/usun", data={"submit": "1"})
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Zajecia, z_id) is not None
