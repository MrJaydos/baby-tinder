"""
Run this once to normalise all origins directly in names.db (the source DB).

Usage inside the Docker container:
    docker-compose run --rm web python fix_origins.py
"""
import sqlite3, os

_ORIGIN_LOOKUP = {
    'old english': 'English', 'middle english': 'English',
    'anglo-saxon': 'English', 'anglo saxon': 'English', 'british': 'English',
    'old french': 'French', 'middle french': 'French', 'old provençal': 'French',
    'old german': 'German', 'old high german': 'German',
    'middle high german': 'German', 'germanic': 'German',
    'old norse': 'Scandinavian', 'norse': 'Scandinavian',
    'swedish': 'Scandinavian', 'norwegian': 'Scandinavian',
    'danish': 'Scandinavian', 'icelandic': 'Scandinavian',
    'old icelandic': 'Scandinavian', 'old scandinavian': 'Scandinavian',
    'irish gaelic': 'Irish', 'old irish': 'Irish',
    'scottish gaelic': 'Scottish',
    'gaelic': 'Celtic', 'cornish': 'Celtic', 'manx': 'Celtic', 'breton': 'Celtic',
    'ancient greek': 'Greek', 'greek mythology': 'Greek',
    'hindi': 'Indian', 'hindu': 'Indian', 'sanskrit': 'Indian',
    'bengali': 'Indian', 'tamil': 'Indian', 'telugu': 'Indian',
    'kannada': 'Indian', 'punjabi': 'Indian', 'gujarati': 'Indian',
    'marathi': 'Indian', 'urdu': 'Indian', 'sikh': 'Indian',
    'nigerian': 'African', 'yoruba': 'African', 'swahili': 'African',
    'zulu': 'African', 'somali': 'African', 'ethiopian': 'African',
    'ghanaian': 'African', 'kenyan': 'African',
    'west african': 'African', 'east african': 'African',
    'south african': 'African', 'north african': 'African',
    'central african': 'African',
    'african-american': 'African', 'african american': 'African',
    'native american': 'American', 'latin american': 'American',
    'south american': 'American', 'central american': 'American',
    'north american': 'American',
    'aztec': 'American', 'mayan': 'American',
    'russian': 'Slavic', 'polish': 'Slavic', 'czech': 'Slavic',
    'serbian': 'Slavic', 'croatian': 'Slavic', 'bulgarian': 'Slavic',
    'ukrainian': 'Slavic', 'slovak': 'Slavic', 'lithuanian': 'Slavic',
    'latvian': 'Slavic', 'romanian': 'Slavic', 'east slavic': 'Slavic',
    'iranian': 'Persian', 'afghan': 'Persian', 'kurdish': 'Persian',
    'flemish': 'Dutch', 'brazilian': 'Portuguese',
    'galician': 'Spanish', 'mexican': 'Spanish', 'catalan': 'Spanish',
    'new zealand maori': 'Maori', 'aboriginal': 'Australian',
    'east coast': '', 'east town': '', 'west leigh': '',
    'new york city': '', 'new zealand': '', 'south africa': '',
    'south wales': '', 'middle east': '', 'anglo': '',
}

_STRIP_PREFIXES = ('Old ', 'Middle ', 'Ancient ', 'Early ', 'Modern ')
_STRIP_SUFFIXES = (' Mythology', ' Gaelic', ' Language')


def normalize(raw):
    if not raw:
        return raw
    s = raw.strip()
    low = s.lower()
    if low.startswith(('combination', 'a combination', 'blend of', 'a blend')):
        return 'Combination'
    for noise in ('variant of ', 'variation of ', 'diminutive of ', 'derived from ',
                  'a form of ', 'a name ', 'a modern ', 'a type ', 'form of '):
        if low.startswith(noise):
            return ''
    mapped = _ORIGIN_LOOKUP.get(low)
    if mapped is not None:
        return mapped
    for prefix in _STRIP_PREFIXES:
        if s.startswith(prefix):
            remainder = s[len(prefix):].strip()
            return _ORIGIN_LOOKUP.get(remainder.lower(), remainder)
    for suffix in _STRIP_SUFFIXES:
        if s.endswith(suffix):
            remainder = s[:-len(suffix)].strip()
            return _ORIGIN_LOOKUP.get(remainder.lower(), remainder)
    if ' - ' in s:
        head = s.split(' - ')[0].strip()
        return _ORIGIN_LOOKUP.get(head.lower(), head)
    if 'american' in low:
        return 'American'
    if 'african' in low:
        return 'African'
    if len(s) > 35:
        return ''
    return s


db_path = os.path.join(os.path.dirname(__file__), 'names.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT id, origin FROM names WHERE origin IS NOT NULL AND origin != ''")
rows = cur.fetchall()

updated = 0
for row_id, origin in rows:
    new_origin = normalize(origin) or None
    if new_origin != origin:
        cur.execute("UPDATE names SET origin = ? WHERE id = ?", (new_origin, row_id))
        updated += 1

conn.commit()
conn.close()
print(f'Done — updated {updated} of {len(rows)} origins in names.db')
