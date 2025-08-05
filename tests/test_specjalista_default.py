from app import db
from app.models import User, Beneficjent, Zajecia


def test_specjalista_default_and_filename(app, client):
    with app.app_context():
        user = User(
            full_name="user",
            email="user@example.com",
            session_type="Dr Who",
        )
        user.set_password("secret")
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        benef = Beneficjent(
            imie="Anna", wojewodztwo="Mazowieckie", user_id=user.id
        )
        db.session.add(benef)
        db.session.commit()
        b_id = benef.id

    client.post(
        "/login",
        data={"email": "user@example.com", "password": "secret"},
        follow_redirects=True,
    )

    resp = client.get("/zajecia/nowe")
    html = resp.get_data(as_text=True)
    assert 'value="Dr Who"' in html

    client.post(
        "/zajecia/nowe",
        data={
            "data": "2023-01-02",
            "godzina_od": "09:00",
            "godzina_do": "10:00",
            "specjalista": "Dr Who",
            "beneficjenci": str(b_id),
        },
        follow_redirects=True,
    )

    with app.app_context():
        zaj = Zajecia.query.one()
        z_id = zaj.id

    resp = client.get(f"/zajecia/{z_id}/docx")
    assert resp.status_code == 200
    disposition = resp.headers.get("Content-Disposition", "")
    assert "Konsultacje z Dr Who" in disposition
