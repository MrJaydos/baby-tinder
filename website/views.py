from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from . import db
from .models import BabyName, Swipe, Match, Couple, User
import os

views = Blueprint('views', __name__)


@views.route('/')
@login_required
def home():
    match_count = 0
    partner = None
    if current_user.couple_id:
        match_count = Match.query.filter_by(couple_id=current_user.couple_id).count()
        partner = User.query.filter(
            User.couple_id == current_user.couple_id,
            User.id != current_user.id
        ).first()
    swipe_count = Swipe.query.filter_by(user_id=current_user.id).count()
    return render_template('home.html', user=current_user, match_count=match_count,
                           swipe_count=swipe_count, partner=partner)


@views.route('/couple', methods=['GET', 'POST'])
@login_required
def couple():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            if current_user.couple_id:
                flash('You are already in a couple.', category='error')
            else:
                new_couple = Couple()
                db.session.add(new_couple)
                db.session.flush()
                current_user.couple_id = new_couple.id
                db.session.commit()
                flash(f'Couple created! Share your code with your partner: {new_couple.code}', category='success')
                return redirect(url_for('views.home'))

        elif action == 'join':
            code = request.form.get('code', '').strip().upper()
            target = Couple.query.filter_by(code=code).first()
            if not target:
                flash('Invalid couple code. Check with your partner and try again.', category='error')
            elif current_user.couple_id == target.id:
                flash("You're already in this couple.", category='error')
            elif len(target.users) >= 2:
                flash('This couple already has two members.', category='error')
            else:
                current_user.couple_id = target.id
                db.session.commit()
                flash('Joined! You and your partner are now connected.', category='success')
                return redirect(url_for('views.home'))

        elif action == 'leave':
            current_user.couple_id = None
            db.session.commit()
            flash('You have left the couple.', category='success')
            return redirect(url_for('views.couple'))

    return render_template('couple.html', user=current_user)


@views.route('/tinder')
@login_required
def tinder():
    return render_template('tinder.html', user=current_user)


@views.route('/api/next-name')
@login_required
def next_name():
    gender = current_user.pref_gender or 'all'
    origin = current_user.pref_origin or 'all'
    style = current_user.pref_style or 'all'

    swiped = db.session.query(Swipe.name_id).filter_by(user_id=current_user.id).subquery()
    query = BabyName.query.filter(BabyName.id.notin_(swiped))

    if gender != 'all':
        query = query.filter(BabyName.gender == gender.upper())
    if origin and origin != 'all':
        query = query.filter(BabyName.origin == origin)
    if style and style != 'all':
        query = query.filter(BabyName.style == style)

    name = query.order_by(db.func.random()).first()

    from flask import make_response
    if not name:
        resp = make_response(jsonify({'done': True}))
    else:
        resp = make_response(jsonify({
            'done': False,
            'id': name.id,
            'name': name.name,
            'gender': name.gender,
            'origin': name.origin or '',
            'meaning': name.meaning or '',
            'style': name.style or '',
        }))
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@views.route('/api/swipe', methods=['POST'])
@login_required
def swipe():
    data = request.get_json(silent=True) or {}
    name_id = data.get('name_id')
    liked = data.get('liked')

    if name_id is None or liked is None:
        return jsonify({'error': 'Missing name_id or liked'}), 400

    if Swipe.query.filter_by(user_id=current_user.id, name_id=name_id).first():
        return jsonify({'error': 'Already swiped'}), 400

    db.session.add(Swipe(user_id=current_user.id, name_id=name_id, liked=liked))
    db.session.commit()

    matched = False
    matched_name = None
    if liked and current_user.couple_id:
        partner = User.query.filter(
            User.couple_id == current_user.couple_id,
            User.id != current_user.id
        ).first()
        if partner:
            partner_liked = Swipe.query.filter_by(
                user_id=partner.id, name_id=name_id, liked=True
            ).first()
            if partner_liked and not Match.query.filter_by(
                couple_id=current_user.couple_id, name_id=name_id
            ).first():
                db.session.add(Match(couple_id=current_user.couple_id, name_id=name_id))
                db.session.commit()
                matched = True
                matched_name = BabyName.query.get(name_id).name

    return jsonify({'success': True, 'matched': matched, 'matched_name': matched_name})


@views.route('/matches')
@login_required
def matches():
    if not current_user.couple_id:
        flash('Set up your couple first to see your matches.', category='error')
        return redirect(url_for('views.couple'))

    all_matches = (Match.query
                   .filter_by(couple_id=current_user.couple_id)
                   .order_by(Match.created_at.desc())
                   .all())
    return render_template('matches.html', user=current_user, matches=all_matches)


@views.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    origins = [row[0] for row in
               db.session.query(BabyName.origin).distinct()
               .filter(BabyName.origin.isnot(None), BabyName.origin != '')
               .order_by(BabyName.origin).all()]
    styles = [row[0] for row in
              db.session.query(BabyName.style).distinct()
              .filter(BabyName.style.isnot(None), BabyName.style != '')
              .order_by(BabyName.style).all()]

    if request.method == 'POST' and request.form.get('action') == 'save_prefs':
        current_user.pref_gender = request.form.get('pref_gender', 'all')
        current_user.pref_origin = request.form.get('pref_origin', '')
        current_user.pref_style = request.form.get('pref_style', '')
        db.session.commit()
        flash('Preferences saved!', category='success')
        return redirect(url_for('views.account'))

    partner = None
    if current_user.couple_id:
        partner = User.query.filter(
            User.couple_id == current_user.couple_id,
            User.id != current_user.id
        ).first()

    return render_template('account.html', user=current_user, partner=partner,
                           origins=origins, styles=styles)


# ── Image generation ──────────────────────────────────────────────────────────

@views.route('/api/name-image/<int:name_id>')
@login_required
def name_image(name_id):
    img_dir = current_app.config['IMAGE_DIR']
    os.makedirs(img_dir, exist_ok=True)
    img_path = os.path.join(img_dir, f'{name_id}.jpg')

    if os.path.exists(img_path):
        return send_file(img_path, mimetype='image/jpeg')

    name = BabyName.query.get_or_404(name_id)
    prompt = _build_prompt(name)

    try:
        local_url = current_app.config.get('IMAGE_API_URL', '')
        img_bytes = _generate_local(local_url, prompt) if local_url else _generate_pollinations(prompt, seed=name_id)
        if img_bytes:
            with open(img_path, 'wb') as f:
                f.write(img_bytes)
            return send_file(img_path, mimetype='image/jpeg')
    except Exception as e:
        current_app.logger.warning(f'Image generation failed for name {name_id}: {e}')

    return '', 404


def _build_prompt(name):
    gender_word = {'M': 'baby boy', 'F': 'baby girl'}.get(name.gender, 'baby')
    origin_part = f', {name.origin} heritage' if name.origin else ''
    return (
        f'adorable {gender_word}{origin_part}, soft watercolour storybook '
        f'illustration, cute toddler portrait, white background, '
        f'pastel colours, no text, no watermark, high quality'
    )


def _generate_pollinations(prompt, seed=42):
    import requests as req
    from urllib.parse import quote
    url = (
        f'https://image.pollinations.ai/prompt/{quote(prompt)}'
        f'?width=320&height=320&nologo=true&seed={seed}&model=flux'
    )
    resp = req.get(url, timeout=90)
    resp.raise_for_status()
    return resp.content


def _generate_local(base_url, prompt):
    """Call a local AUTOMATIC1111 /sdapi/v1/txt2img endpoint."""
    import requests as req, base64
    resp = req.post(f'{base_url}/sdapi/v1/txt2img', json={
        'prompt': prompt,
        'negative_prompt': 'realistic photo, text, watermark, ugly, deformed, nsfw',
        'width': 320, 'height': 320,
        'steps': 20, 'cfg_scale': 7,
    }, timeout=300)
    resp.raise_for_status()
    return base64.b64decode(resp.json()['images'][0])
