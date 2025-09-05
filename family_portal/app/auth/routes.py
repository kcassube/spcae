from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, NotificationPreference
from app.auth.forms import LoginForm, RegistrationForm
from urllib.parse import urlparse  # Werkzeug 3 entfernt url_parse
from app import db
from app.auth import bp

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Ungültiger Benutzername oder Passwort')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        # Nur interne relative Pfade erlauben (Schutz vor Open Redirect)
        if not next_page:
            next_page = url_for('main.index')
        else:
            parsed = urlparse(next_page)
            if parsed.netloc or parsed.scheme:
                next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('auth/login.html', title='Anmelden', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Duplikatsprüfungen (verhindert IntegrityError 500)
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        duplicate = False
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben')
            duplicate = True
        if User.query.filter_by(email=email).first():
            flash('E-Mail bereits registriert')
            duplicate = True
        if duplicate:
            return render_template('auth/register.html', title='Registrieren', form=form)
        user = User(username=username, email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # Default Preferences: alle aktiv für email + socket
    defaults = ['events','chat','photos','system']  # finance entfernt
        for kind in defaults:
            db.session.add(NotificationPreference(user_id=user.id, channel='email', kind=kind, enabled=True))
            db.session.add(NotificationPreference(user_id=user.id, channel='socket', kind=kind, enabled=True))
        db.session.commit()
        flash('Glückwunsch, Sie sind nun registriert!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Registrieren', form=form)
