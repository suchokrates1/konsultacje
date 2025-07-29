from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    default_duration = db.Column(db.Integer, default=90)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Dodaj pod istniejącym modelem User


class Beneficjent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imie = db.Column(db.String(100), nullable=False)
    wojewodztwo = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Zajecia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    godzina_od = db.Column(db.Time, nullable=False)
    godzina_do = db.Column(db.Time, nullable=False)
    specjalista = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    beneficjenci = db.relationship(
        'Beneficjent', secondary='zajecia_beneficjenci'
    )


# Tabela relacyjna: wielu beneficjentów na zajęciach
zajecia_beneficjenci = db.Table(
    'zajecia_beneficjenci',
    db.Column('zajecia_id', db.Integer, db.ForeignKey('zajecia.id')),
    db.Column('beneficjent_id', db.Integer, db.ForeignKey('beneficjent.id')),
)
