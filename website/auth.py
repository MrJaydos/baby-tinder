from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required, login_user, logout_user, current_user
from .models import User
from . import db

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            flash(f'Welcome back, {user.first_name}!', category='success')
            return redirect(url_for('views.home'))
        flash('Incorrect email or password.', category='error')

    return render_template('login.html', user=current_user)


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('firstName', '').strip()
        password1 = request.form.get('password1', '')
        password2 = request.form.get('password2', '')

        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be at least 4 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be at least 2 characters.', category='error')
        elif password1 != password2:
            flash("Passwords don't match.", category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            user = User(
                email=email,
                first_name=first_name,
                password=generate_password_hash(password1, method='pbkdf2:sha256'),
            )
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash('Account created! Now set up your couple.', category='success')
            return redirect(url_for('views.couple'))

    return render_template('sign-up.html', user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
