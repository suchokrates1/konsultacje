from datetime import date, time

from sqlalchemy import text

from app import db
from app.models import User, Zajecia, SentEmail


def test_deleting_session_removes_sent_emails(app):
    with app.app_context():
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        user = User(full_name="user", email="user@example.com")
        user.set_password("secret")
        user.confirmed = True
        db.session.add(user)
        db.session.commit()

        session = Zajecia(
            data=date(2023, 1, 1),
            godzina_od=time(9, 0),
            godzina_do=time(10, 0),
            specjalista="spec",
            user_id=user.id,
        )
        db.session.add(session)
        db.session.commit()

        email = SentEmail(
            zajecia=session,
            recipient="dest@example.com",
            subject="hello",
            status="sent",
        )
        db.session.add(email)
        db.session.commit()

        db.session.delete(session)
        db.session.commit()

        assert db.session.get(Zajecia, session.id) is None
        assert SentEmail.query.count() == 0
