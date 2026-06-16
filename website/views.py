from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from . import db
from .models import BabyName, Swipe, Match, Couple, User

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
    if not name:
        return jsonify({'done': True})

    return jsonify({
        'done': False,
        'id': name.id,
        'name': name.name,
        'gender': name.gender,
        'origin': name.origin or '',
        'meaning': name.meaning or '',
        'style': name.style or '',
    })


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
