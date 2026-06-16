from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from os import path
import os

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    database_url = os.environ.get('DATABASE_URL', f'sqlite:///{path.join(app.instance_path, "database.db")}')
    # Heroku/Coolify may give postgres:// which SQLAlchemy requires as postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Image generation — lazily cached to disk
    app.config['IMAGE_DIR'] = os.environ.get(
        'IMAGE_DIR', os.path.join(app.instance_path, 'images'))
    # Optional: point at a local AUTOMATIC1111 instance for fully offline generation
    # e.g. IMAGE_API_URL=http://localhost:7860
    app.config['IMAGE_API_URL'] = os.environ.get('IMAGE_API_URL', '')

    db.init_app(app)

    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User

    os.makedirs(app.instance_path, exist_ok=True)
    with app.app_context():
        db.create_all()
        _migrate_db()
        _auto_load_names(app)
        _migrate_origins()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app


def _migrate_db():
    """Add columns introduced after initial schema creation."""
    from sqlalchemy import text
    new_cols = [
        ('pref_gender', "VARCHAR(10) NOT NULL DEFAULT 'all'"),
        ('pref_origin', "VARCHAR(100) NOT NULL DEFAULT ''"),
        ('pref_style',  "VARCHAR(100) NOT NULL DEFAULT ''"),
    ]
    with db.engine.connect() as conn:
        for col_name, col_def in new_cols:
            try:
                conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {col_name} {col_def}'))
                conn.commit()
            except Exception:
                pass  # Column already exists


def _normalize_origin(raw):
    """Normalize messy origins: 'American - English' → 'American', 'Combination of X and Y' → 'Combination'."""
    if not raw:
        return raw
    s = raw.strip()
    low = s.lower()
    if low.startswith(('combination', 'a combination', 'blend of', 'a blend')):
        return 'Combination'
    if ' - ' in s:
        return s.split(' - ')[0].strip()
    return s


def _auto_load_names(app):
    from .models import BabyName
    if BabyName.query.count() > 0:
        return

    src_path = path.join(app.root_path, '..', 'names.db')
    if not path.exists(src_path):
        return

    import sqlite3
    gender_map = {
        'boy': 'M', 'male': 'M', 'm': 'M',
        'girl': 'F', 'female': 'F', 'f': 'F',
        'neutral': 'N', 'unisex': 'N', 'n': 'N', 'u': 'N',
    }
    count = 0
    conn = sqlite3.connect(src_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT name, gender, origin, meaning, style FROM names')
    for row in cur.fetchall():
        name_val = (row['name'] or '').strip()
        if not name_val:
            continue
        raw_gender = (row['gender'] or '').strip().lower()
        gender = gender_map.get(raw_gender, 'N')
        raw_origin = (row['origin'] or '').strip()
        db.session.add(BabyName(
            name=name_val,
            gender=gender,
            origin=_normalize_origin(raw_origin) or None,
            meaning=(row['meaning'] or '').strip() or None,
            style=(row['style'] or '').strip() or None,
        ))
        count += 1
    conn.close()

    db.session.commit()
    print(f'Auto-loaded {count} baby names from names.db')


def _migrate_origins():
    """Normalize compound / descriptive origins already in the DB."""
    from .models import BabyName, User
    from sqlalchemy import or_
    updated = 0

    for n in BabyName.query.filter(
        or_(BabyName.origin.like('% - %'),
            BabyName.origin.ilike('Combination%'),
            BabyName.origin.ilike('Blend of%'))
    ).all():
        condensed = _normalize_origin(n.origin)
        if condensed != n.origin:
            n.origin = condensed
            updated += 1

    for u in User.query.filter(
        or_(User.pref_origin.like('% - %'),
            User.pref_origin.ilike('Combination%'))
    ).all():
        condensed = _normalize_origin(u.pref_origin)
        if condensed != u.pref_origin:
            u.pref_origin = condensed
            updated += 1

    if updated:
        db.session.commit()
        print(f'Normalized {updated} origin values')
