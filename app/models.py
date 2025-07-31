"""Database models used by the application."""

from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager
from itsdangerous import URLSafeTimedSerializer
from flask import current_app


class Roles:
    ADMIN = "admin"
    INSTRUCTOR = "instructor"


class User(UserMixin, db.Model):
    """Application user capable of logging in and resetting a password."""
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    default_duration = db.Column(db.Integer, default=90)
    role = db.Column(db.String(20), default=Roles.INSTRUCTOR)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
        except Exception:
            return None
        return db.session.get(User, data.get('user_id'))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Additional application models


class Beneficjent(db.Model):
    """Person receiving consultations stored for a particular user."""
    id = db.Column(db.Integer, primary_key=True)
    imie = db.Column(db.String(100), nullable=False)
    wojewodztwo = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User')


class Zajecia(db.Model):
    """Scheduled consultation session with related beneficiaries."""
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    godzina_od = db.Column(db.Time, nullable=False)
    godzina_do = db.Column(db.Time, nullable=False)
    specjalista = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User')

    beneficjenci = db.relationship(
        'Beneficjent', secondary='zajecia_beneficjenci'
    )


# Tabela relacyjna: wielu beneficjentów na zajęciach
zajecia_beneficjenci = db.Table(
    'zajecia_beneficjenci',
    db.Column('zajecia_id', db.Integer, db.ForeignKey('zajecia.id')),
    db.Column('beneficjent_id', db.Integer, db.ForeignKey('beneficjent.id')),
)
