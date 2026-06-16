from . import db
from flask_login import UserMixin
from datetime import datetime
import secrets
import string


def _gen_couple_code():
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(6))


class Couple(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, default=_gen_couple_code)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    users = db.relationship('User', backref='couple', lazy=True)
    matches = db.relationship('Match', backref='couple', lazy=True)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    couple_id = db.Column(db.Integer, db.ForeignKey('couple.id'), nullable=True)
    swipes = db.relationship('Swipe', backref='user', lazy=True)
    pref_gender = db.Column(db.String(10), nullable=False, default='all')
    pref_origin = db.Column(db.String(100), nullable=False, default='')
    pref_style = db.Column(db.String(100), nullable=False, default='')


class BabyName(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(1), nullable=False, default='N')  # M, F, N
    origin = db.Column(db.String(100))
    meaning = db.Column(db.Text)
    style = db.Column(db.String(100))


class Swipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name_id = db.Column(db.Integer, db.ForeignKey('baby_name.id'), nullable=False)
    liked = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'name_id'),)


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couple.id'), nullable=False)
    name_id = db.Column(db.Integer, db.ForeignKey('baby_name.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    baby_name = db.relationship('BabyName')
    __table_args__ = (db.UniqueConstraint('couple_id', 'name_id'),)
