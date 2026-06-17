from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from os import path
import os

db = SQLAlchemy()

# Canonical origin mapping — applied at import time and on every startup migration.
# Keys are matched case-insensitively. Empty string '' means "discard this origin".
_ORIGIN_LOOKUP = {
    # Old / Middle / Ancient prefixes → base language (also handled generically below)
    'old english':        'English',
    'middle english':     'English',
    'anglo-saxon':        'English',
    'anglo saxon':        'English',
    'british':            'English',
    'anglo-norman':       'English',
    'early modern english': 'English',
    'old french':         'French',
    'middle french':      'French',
    'old provençal':      'French',
    'norman':             'French',
    'norman french':      'French',
    'occitan':            'French',
    'old german':         'German',
    'old high german':    'German',
    'middle high german': 'German',
    'germanic':           'German',
    'low german':         'German',
    'middle low german':  'German',
    'old low german':     'German',
    'old saxon':          'German',
    'frankish':           'German',
    'swiss german':       'German',
    'bavarian':           'German',
    'austrian':           'German',
    'old norse':          'Scandinavian',
    'norse':              'Scandinavian',
    'swedish':            'Scandinavian',
    'norwegian':          'Scandinavian',
    'danish':             'Scandinavian',
    'icelandic':          'Scandinavian',
    'old icelandic':      'Scandinavian',
    'old scandinavian':   'Scandinavian',
    'irish gaelic':       'Irish',
    'old irish':          'Irish',
    'scottish gaelic':    'Scottish',
    'gaelic':             'Celtic',
    'cornish':            'Celtic',
    'manx':               'Celtic',
    'breton':             'Celtic',
    'ancient greek':      'Greek',
    'greek mythology':    'Greek',
    'modern greek':       'Greek',
    'byzantine':          'Greek',
    'byzantine greek':    'Greek',
    'hellenistic':        'Greek',
    'hellenic':           'Greek',
    # South Asian → Indian
    'hindi':              'Indian',
    'hindu':              'Indian',
    'sanskrit':           'Indian',
    'bengali':            'Indian',
    'tamil':              'Indian',
    'telugu':             'Indian',
    'kannada':            'Indian',
    'punjabi':            'Indian',
    'gujarati':           'Indian',
    'marathi':            'Indian',
    'urdu':               'Indian',
    'sikh':               'Indian',
    # Scandinavian already above (Swedish, Norwegian, Danish, Icelandic → Scandinavian)
    # Sub-Saharan / regional African → African
    'nigerian':           'African',
    'yoruba':             'African',
    'swahili':            'African',
    'zulu':               'African',
    'somali':             'African',
    'ethiopian':          'African',
    'ghanaian':           'African',
    'west african':       'African',
    'east african':       'African',
    'south african':      'African',
    'north african':      'African',
    'central african':    'African',
    'kenyan':             'African',
    'african-american':   'African',
    'african american':   'African',
    # Slavic languages → Slavic
    'russian':            'Slavic',
    'polish':             'Slavic',
    'czech':              'Slavic',
    'serbian':            'Slavic',
    'croatian':           'Slavic',
    'bulgarian':          'Slavic',
    'ukrainian':          'Slavic',
    'slovak':             'Slavic',
    'lithuanian':         'Slavic',
    'latvian':            'Slavic',
    'romanian':           'Slavic',
    'east slavic':        'Slavic',
    # Arabic
    'classical arabic':   'Arabic',
    'modern arabic':      'Arabic',
    'arabian':            'Arabic',
    'quranic':            'Arabic',
    'koranic':            'Arabic',
    'islamic':            'Arabic',
    'muslim':             'Arabic',
    # Biblical → the underlying language
    'biblical':           'Hebrew',
    'biblical hebrew':    'Hebrew',
    'biblical greek':     'Greek',
    'biblical aramaic':   'Hebrew',
    'old testament':      'Hebrew',
    'new testament':      'Greek',
    'hebrew (biblical)':  'Hebrew',
    # Fusion → Combination
    'fusion':             'Combination',
    # Middle Eastern → Persian (for name purposes)
    'iranian':            'Persian',
    'afghan':             'Persian',
    'kurdish':            'Persian',
    # Other consolidations
    'flemish':            'Dutch',
    'brazilian':          'Portuguese',
    'galician':           'Spanish',
    'mexican':            'Spanish',
    'catalan':            'Spanish',
    'aztec':              'American',
    'mayan':              'American',
    'native american':    'American',
    'latin american':     'American',
    'south american':     'American',
    'central american':   'American',
    'north american':     'American',
    'new zealand maori':  'Maori',
    'aboriginal':         'Australian',
    # Discard entries that are not real cultural origins
    'east coast':         '',
    'east town':          '',
    'west leigh':         '',
    'new york city':      '',
    'new zealand':        '',
    'south africa':       '',
    'south wales':        '',
    'middle east':        '',
    'anglo':              '',
}

# Prefixes to strip (e.g. "Old Welsh" → "Welsh", "Biblical Hebrew" → "Hebrew")
_STRIP_PREFIXES = ('Old ', 'Middle ', 'Ancient ', 'Early ', 'Modern ', 'Biblical ')
# Suffixes to strip (e.g. "Greek Mythology" → "Greek", "Scottish Gaelic" → "Scottish")
_STRIP_SUFFIXES = (' Mythology', ' Gaelic', ' Language')


def _normalize_origin(raw):
    """Map messy/compound/redundant origins to a clean canonical form."""
    if not raw:
        return raw
    s = raw.strip()
    low = s.lower()

    # Descriptive combination phrases → Combination
    if low.startswith(('combination', 'a combination', 'blend of', 'a blend')):
        return 'Combination'

    # Other descriptive/noise phrases → discard
    for noise in ('variant of ', 'variation of ', 'diminutive of ', 'derived from ',
                  'a form of ', 'a name ', 'a modern ', 'a type ', 'form of '):
        if low.startswith(noise):
            return ''

    # Exact lookup (case-insensitive)
    mapped = _ORIGIN_LOOKUP.get(low)
    if mapped is not None:
        return mapped  # may be '' (discard)

    # Generic prefix stripping: "Old Welsh" → "Welsh"
    for prefix in _STRIP_PREFIXES:
        if s.startswith(prefix):
            remainder = s[len(prefix):].strip()
            # Re-run lookup on the stripped value
            return _ORIGIN_LOOKUP.get(remainder.lower(), remainder)

    # Suffix stripping: "X Mythology" → "X"
    for suffix in _STRIP_SUFFIXES:
        if s.endswith(suffix):
            remainder = s[:-len(suffix)].strip()
            return _ORIGIN_LOOKUP.get(remainder.lower(), remainder)

    # Compound with dash separator: "American - English" → "American"
    if ' - ' in s:
        head = s.split(' - ')[0].strip()
        return _ORIGIN_LOOKUP.get(head.lower(), head)

    # Catch-all for remaining geographic/cultural variants
    if 'american' in low:
        return 'American'
    if 'african' in low:
        return 'African'
    if 'fusion' in low:
        return 'Combination'
    if 'biblical' in low:
        return 'Hebrew'
    if 'arabic' in low:
        return 'Arabic'

    # Too long → almost certainly garbled data, discard
    if len(s) > 35:
        return ''

    return s


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    database_url = os.environ.get('DATABASE_URL', f'sqlite:///{path.join(app.instance_path, "database.db")}')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['IMAGE_DIR'] = os.environ.get(
        'IMAGE_DIR', os.path.join(app.instance_path, 'images'))
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
                pass


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
        normalized = _normalize_origin(raw_origin) or None
        db.session.add(BabyName(
            name=name_val,
            gender=gender,
            origin=normalized,
            meaning=(row['meaning'] or '').strip() or None,
            style=(row['style'] or '').strip() or None,
        ))
        count += 1
    conn.close()

    db.session.commit()
    print(f'Auto-loaded {count} baby names from names.db')


def _migrate_origins():
    """Apply the full normalization table to all existing records in the DB."""
    from .models import BabyName, User
    updated = 0

    for n in BabyName.query.filter(BabyName.origin.isnot(None)).all():
        normalized = _normalize_origin(n.origin) or None
        if normalized != n.origin:
            n.origin = normalized
            updated += 1

    for u in User.query.filter(User.pref_origin != '').all():
        normalized = _normalize_origin(u.pref_origin) or ''
        if normalized != u.pref_origin:
            u.pref_origin = normalized
            updated += 1

    if updated:
        db.session.commit()
        print(f'Normalized {updated} origin values')
