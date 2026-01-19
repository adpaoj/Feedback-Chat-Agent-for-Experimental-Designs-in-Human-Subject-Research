from flask import render_template, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import bp
from app.models import User
from app.extensions import db

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    Redirects to the main index page if successful.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            return render_template('login.html', error='Invalid username or password.')

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    """
    Handle user logout.
    """
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    Requires a valid registration token.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        token = request.form['token']

        if token != current_app.config['REGISTRATION_TOKEN']:
            return render_template('register.html', error='Invalid registration token.')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error='Username already taken.')

        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('main.index'))

    return render_template('register.html')
