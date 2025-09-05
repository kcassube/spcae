from flask import render_template, request, redirect, url_for, flash, send_from_directory, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, uuid, errno
from datetime import datetime
from app import db
from . import bp
from app.models import Photo

ALLOWED_EXT = {'png','jpg','jpeg','gif','webp'}

def _allowed(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXT

def _ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except PermissionError:
        fallback = '/tmp/family_portal_fallback/photos'
        try:
            os.makedirs(fallback, exist_ok=True)
            return fallback
        except Exception:
            raise
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return path

def _upload_dir():
    base = current_app.config.get('UPLOAD_BASE') or '/tmp'
    target = os.path.join(base, 'photos')
    return _ensure_dir(target)

@bp.route('/')
@login_required
def index():
    photos = Photo.query.filter_by(user_id=current_user.id).order_by(Photo.created_at.desc()).limit(200).all()
    return render_template('photos/index.html', photos=photos)

@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    f = request.files.get('file')
    title = (request.form.get('title') or '').strip()[:120]
    if not f or f.filename == '':
        flash('Keine Datei','error')
        return redirect(url_for('photos.index'))
    if not _allowed(f.filename):
        flash('Dateityp nicht erlaubt','error')
        return redirect(url_for('photos.index'))
    ext = f.filename.rsplit('.',1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(_upload_dir(), secure_filename(fname))
    f.save(path)
    p = Photo(user_id=current_user.id, filename=fname, title=title, created_at=datetime.utcnow())
    db.session.add(p)
    db.session.commit()
    flash('Hochgeladen','ok')
    return redirect(url_for('photos.index'))

@bp.route('/raw/<fname>')
@login_required
def raw(fname):
    return send_from_directory(_upload_dir(), fname, as_attachment=False)

@bp.route('/download/<fname>')
@login_required
def download(fname):
    """Ermöglicht direkten Download (Content-Disposition Attachment)."""
    return send_from_directory(_upload_dir(), fname, as_attachment=True)

@bp.route('/api/delete/<int:photo_id>', methods=['DELETE','POST'])
@login_required
def delete_photo(photo_id):
    p = Photo.query.get_or_404(photo_id)
    if p.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error':'Unauthorized'}),403
    # Datei entfernen (Best Effort)
    try:
        path = os.path.join(_upload_dir(), p.filename)
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass
    from app import db
    db.session.delete(p)
    db.session.commit()
    return jsonify({'status':'deleted','id':photo_id})

@bp.route('/api/list')
@login_required
def api_list():
    photos = Photo.query.filter_by(user_id=current_user.id).order_by(Photo.created_at.desc()).all()
    return jsonify([{'id':p.id,'title':p.title,'filename':p.filename,'created_at':p.created_at.isoformat()} for p in photos])
