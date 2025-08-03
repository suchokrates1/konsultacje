from app import db
from app.models import User


def test_allows_duplicate_full_name(app):
    """Multiple users can share the same full name."""
    with app.app_context():
        user1 = User(full_name='duplicate', email='user1@example.com')
        user1.set_password('pass1')
        db.session.add(user1)
        db.session.commit()

        user2 = User(full_name='duplicate', email='user2@example.com')
        user2.set_password('pass2')
        db.session.add(user2)
        db.session.commit()

        users = User.query.filter_by(full_name='duplicate').all()
        assert len(users) == 2
