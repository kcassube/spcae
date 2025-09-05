from flask import render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, uuid, errno
from datetime import datetime
from app import db
from . import bp
from app.models import UserProfile, get_or_create_profile, NotificationPreference

ALLOWED_AVATAR = {'png','jpg','jpeg','gif','webp'}

def _ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except PermissionError:
        fallback = '/tmp/family_portal_fallback/avatars'
        try:
            os.makedirs(fallback, exist_ok=True)
            return fallback
        except Exception:
            raise
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return path

def _avatar_dir():
    base = current_app.config.get('UPLOAD_BASE') or '/tmp'
    target = os.path.join(base, 'avatars')
    return _ensure_dir(target)

@bp.route('/', methods=['GET','POST'])
@login_required
def index():
    profile = get_or_create_profile(current_user)
    if request.method == 'POST':
        bio = (request.form.get('bio') or '').strip()
        profile.bio = bio
        kinds = ['events','chat','photos','system']  # finance entfernt
        channels = ['email','socket']
        # Bestehende Prefs laden in Dict
        existing = {(p.kind, p.channel): p for p in NotificationPreference.query.filter_by(user_id=current_user.id).all()}
        for kind in kinds:
            for ch in channels:
                field = f"pref_{ch}_{kind}"
                enabled = field in request.form
                obj = existing.get((kind,ch))
                if obj:
                    obj.enabled = enabled
                else:
                    db.session.add(NotificationPreference(user_id=current_user.id, channel=ch, kind=kind, enabled=enabled))
        db.session.commit()
        flash('Gespeichert','ok')
        return redirect(url_for('profile.index'))
    # Prefs für Anzeige
    prefs = {(p.channel, p.kind): p.enabled for p in NotificationPreference.query.filter_by(user_id=current_user.id).all()}
    return render_template('profile/index.html', profile=profile, prefs=prefs)

@bp.route('/avatar', methods=['POST'])
@login_required
def avatar():
    profile = get_or_create_profile(current_user)
    f = request.files.get('avatar')
    if not f or f.filename=='':
        flash('Keine Datei','error')
        return redirect(url_for('profile.index'))
    ext = f.filename.rsplit('.',1)[-1].lower()
    if ext not in ALLOWED_AVATAR:
        flash('Typ nicht erlaubt','error')
        return redirect(url_for('profile.index'))
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(_avatar_dir(), secure_filename(fname))
    f.save(path)
    profile.avatar_filename = fname
    profile.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Avatar aktualisiert','ok')
    return redirect(url_for('profile.index'))

@bp.route('/avatar/raw/<fname>')
@login_required
def avatar_raw(fname):
    return send_from_directory(_avatar_dir(), fname, as_attachment=False)
