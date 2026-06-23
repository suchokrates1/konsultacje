"""Tests for project/edition scoping (ATNIS V / ATNIS VI)."""

from datetime import date, time

from app import db
from app.models import Beneficjent, Projekt, ProjectStatus, Roles, User, Zajecia
from app.projekt_utils import get_aktywny_projekt, ustaw_jako_aktywny


def _make_admin(app, email="admin@example.com"):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        user.role = Roles.ADMIN
        db.session.commit()


def test_migration_seeds_projects(app):
    """Fresh database should contain ATNIS V (archive) and ATNIS VI (active)."""
    with app.app_context():
        v = Projekt.query.filter_by(nazwa="ATNIS V").one()
        vi = Projekt.query.filter_by(nazwa="ATNIS VI").one()
        assert v.status == ProjectStatus.ARCHIWUM
        assert vi.status == ProjectStatus.AKTYWNY
        assert get_aktywny_projekt().id == vi.id


def test_instructor_sees_only_active_project(client, app, login):
    """Instructor lists should exclude archived project data."""
    login()
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").one()
        archiwum = Projekt.query.filter_by(nazwa="ATNIS V").one()
        aktywny = get_aktywny_projekt()
        b_old = Beneficjent(
            imie="Stary Beneficjent",
            wojewodztwo="Mazowieckie",
            user_id=user.id,
            project_id=archiwum.id,
        )
        b_new = Beneficjent(
            imie="Nowy Beneficjent",
            wojewodztwo="Mazowieckie",
            user_id=user.id,
            project_id=aktywny.id,
        )
        db.session.add_all([b_old, b_new])
        db.session.flush()
        z_old = Zajecia(
            data=date(2025, 1, 1),
            godzina_od=time(10, 0),
            godzina_do=time(11, 0),
            specjalista="Dietetyk",
            user_id=user.id,
            project_id=archiwum.id,
        )
        z_old.beneficjenci = [b_old]
        z_new = Zajecia(
            data=date(2026, 6, 1),
            godzina_od=time(10, 0),
            godzina_do=time(11, 0),
            specjalista="Dietetyk",
            user_id=user.id,
            project_id=aktywny.id,
        )
        z_new.beneficjenci = [b_new]
        db.session.add_all([z_old, z_new])
        db.session.commit()
        old_id = z_old.id

    resp = client.get("/zajecia")
    text = resp.get_data(as_text=True)
    assert "Nowy Beneficjent" not in text or "2026" in text
    assert "2025-01-01" not in text and "01.01.2025" not in text

    resp = client.get("/beneficjenci")
    text = resp.get_data(as_text=True)
    assert "Nowy Beneficjent" in text
    assert "Stary Beneficjent" not in text

    resp = client.get(f"/zajecia/{old_id}/edytuj", follow_redirects=True)
    assert "Brak dostępu" in resp.get_data(as_text=True)


def test_admin_zajecia_shows_beneficjent_and_project_filter(client, app, login):
    """Admin session list should include beneficiary and respect project filter."""
    login(email="admin@example.com", password="password")
    _make_admin(app)
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(full_name="Instr", email="instr@example.com", confirmed=True)
            user.set_password("password")
            db.session.add(user)
        archiwum = Projekt.query.filter_by(nazwa="ATNIS V").one()
        aktywny = get_aktywny_projekt()
        benef = Beneficjent(
            imie="Jan Kowalski",
            wojewodztwo="Mazowieckie",
            user_id=user.id,
            project_id=aktywny.id,
        )
        db.session.add(benef)
        db.session.flush()
        zaj = Zajecia(
            data=date(2026, 6, 15),
            godzina_od=time(9, 0),
            godzina_do=time(10, 30),
            specjalista="Dietetyk",
            user_id=user.id,
            project_id=aktywny.id,
        )
        zaj.beneficjenci = [benef]
        db.session.add(zaj)
        db.session.commit()
        arch_id = archiwum.id

    resp = client.get("/admin/zajecia")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Jan Kowalski" in text
    assert "Beneficjent" in text

    resp = client.get(f"/admin/zajecia?projekt_id={arch_id}")
    assert resp.status_code == 200
    assert "Jan Kowalski" not in resp.get_data(as_text=True)


def test_activate_project_archives_previous(client, app, login):
    """Setting a new project as active should archive the previous one."""
    login(email="admin@example.com", password="password")
    _make_admin(app)
    with app.app_context():
        vi = get_aktywny_projekt()
        vii = Projekt(nazwa="ATNIS VII", status=ProjectStatus.ARCHIWUM)
        db.session.add(vii)
        db.session.commit()
        vii_id = vii.id
        vi_id = vi.id

    resp = client.post(
        f"/admin/projekty/{vii_id}/aktywuj",
        data={"submit": "Ustaw jako obecny"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "ustawiony jako obecny" in resp.get_data(as_text=True)

    with app.app_context():
        vi = db.session.get(Projekt, vi_id)
        vii = db.session.get(Projekt, vii_id)
        assert vi.status == ProjectStatus.ARCHIWUM
        assert vi.zarchiwizowano is not None
        assert vii.status == ProjectStatus.AKTYWNY
        assert get_aktywny_projekt().id == vii_id


def test_create_project_via_admin(client, app, login):
    """Admin can create a new archived project."""
    login(email="admin@example.com", password="password")
    _make_admin(app)
    resp = client.post(
        "/admin/projekty/nowy",
        data={"nazwa": "ATNIS VIII", "submit": "Zapisz"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        p = Projekt.query.filter_by(nazwa="ATNIS VIII").one()
        assert p.status == ProjectStatus.ARCHIWUM
