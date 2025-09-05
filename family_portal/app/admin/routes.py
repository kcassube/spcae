from flask import render_template, request, redirect, url_for, flash, Response, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, case
from app.admin import bp
from app import db, APP_START
from app.models import User, Event, Message, Photo, AuditLog
from datetime import date, datetime, timedelta
from flask_wtf.csrf import generate_csrf

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Keine Berechtigung.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return wrapper

def _compute_finance_aggregates():
    # Finance entfernt – Rückgabe leerer Struktur für Template-Kompatibilität, falls alte Templates im Cache
    return {
        'month_start': '',
        'total_expenses': 0.0,
        'total_incomes': 0.0,
        'net_balance': 0.0,
        'per_user': [],
        'top_spenders': [],
        'top_categories': []
    }

def _compute_activity_metrics():
    now = datetime.utcnow()
    last_30 = now - timedelta(days=30)
    return {
        'events_30d': db.session.scalar(db.select(func.count(Event.id)).filter(Event.start_time>=last_30)),
        'messages_30d': db.session.scalar(db.select(func.count(Message.id)).filter(Message.timestamp>=last_30)),
        'photos_30d': db.session.scalar(db.select(func.count(Photo.id)).filter(Photo.created_at>=last_30)),
    'expenses_30d': 0,
    }

def _base_stats():
    return {
        'users_total': db.session.scalar(db.select(func.count(User.id))),
        'users_soft_deleted': db.session.scalar(db.select(func.count(User.id)).filter(User.deleted_at.is_not(None))),
        'events_total': db.session.scalar(db.select(func.count(Event.id))),
        'messages_total': db.session.scalar(db.select(func.count(Message.id))),
        'photos_total': db.session.scalar(db.select(func.count(Photo.id)))
    }

@bp.route('/')
@login_required
@admin_required
def index():
    """Legacy Übersicht (Benutzerliste) – verlinkt auf das neue Dashboard."""
    page = request.args.get('page', 1, type=int)
    per_page = 25
    users_pagination = User.query.filter(User.deleted_at.is_(None)).order_by(User.username.asc()).paginate(page=page, per_page=per_page, error_out=False)
    users = users_pagination.items
    return render_template('admin/index.html', users=users, stats=_base_stats(), pagination=users_pagination)

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    finance = _compute_finance_aggregates()
    activity = _compute_activity_metrics()
    recent_events = Event.query.order_by(Event.start_time.desc()).limit(6).all()
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()
    return render_template('admin/dashboard.html', stats=_base_stats(), finance=finance, activity=activity, recent_events=recent_events, audit_logs=audit_logs)

@bp.route('/api/dashboard')
@login_required
@admin_required
def api_dashboard():
    return jsonify({
        'stats': _base_stats(),
        'finance': _compute_finance_aggregates(),
        'activity': _compute_activity_metrics(),
        'audit_latest': [
            {
                'id': l.id,
                'created_at': l.created_at.isoformat() if l.created_at else None,
                'action': l.action,
                'target_type': l.target_type,
                'target_id': l.target_id
            } for l in AuditLog.query.order_by(AuditLog.created_at.desc()).limit(25).all()
        ]
    })

@bp.route('/audit')
@login_required
@admin_required
def audit_list():
    page = request.args.get('page',1,type=int)
    per_page = 50
    action = request.args.get('action')
    search = request.args.get('q','').strip()
    q = AuditLog.query
    if action:
        q = q.filter(AuditLog.action==action)
    if search:
        like = f"%{search}%"
        q = q.filter(AuditLog.details.ilike(like) | AuditLog.action.ilike(like) | AuditLog.target_type.ilike(like))
    q = q.order_by(AuditLog.created_at.desc())
    pag = q.paginate(page=page, per_page=per_page, error_out=False)
    actions = db.session.query(AuditLog.action).distinct().all()
    return render_template('admin/audit_list.html', logs=pag.items, pagination=pag, actions=[a[0] for a in actions], current_action=action, search=search)

@bp.route('/api/audit/search')
@login_required
@admin_required
def audit_search_api():
    limit = min(200, request.args.get('limit', 50, type=int))
    search = request.args.get('q','').strip()
    action = request.args.get('action')
    q = AuditLog.query
    if action:
        q = q.filter(AuditLog.action==action)
    if search:
        like = f"%{search}%"
        q = q.filter(AuditLog.details.ilike(like) | AuditLog.action.ilike(like) | AuditLog.target_type.ilike(like))
    rows = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify([
        {
            'id': r.id,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'action': r.action,
            'target_type': r.target_type,
            'target_id': r.target_id,
            'details': r.details[:400] if r.details else None
        } for r in rows
    ])

@bp.route('/api/users')
@login_required
@admin_required
def api_users():
    show_deleted = bool(request.args.get('show_deleted'))
    q = User.query
    if not show_deleted:
        q = q.filter(User.deleted_at.is_(None))
    search = request.args.get('q','').strip()
    if search:
        like = f"%{search}%"
        q = q.filter(User.username.ilike(like) | User.email.ilike(like))
    users = q.order_by(User.username.asc()).limit(300).all()
    return jsonify([
        {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'is_admin': u.is_admin,
            'deleted_at': u.deleted_at.isoformat() if u.deleted_at else None,
            'photos_count': u.photos.count(),
            'messages_sent': u.messages_sent.count(),
        } for u in users
    ])

@bp.route('/audit/<int:log_id>')
@login_required
@admin_required
def audit_detail(log_id):
    log = AuditLog.query.get_or_404(log_id)
    return render_template('admin/audit_detail.html', log=log)

@bp.route('/user/<int:user_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        new_email = request.form.get('email','').strip()
        is_admin_flag = bool(request.form.get('is_admin'))
        email_changed = False
        if new_email and new_email != user.email:
            if User.query.filter(User.email==new_email, User.id!=user.id).first():
                flash('E-Mail bereits vergeben.')
            else:
                user.email = new_email
                email_changed = True
        old_admin = user.is_admin
        user.is_admin = is_admin_flag
        db.session.commit()
        db.session.add(AuditLog(actor_id=current_user.id, action='edit_user', target_type='user', target_id=str(user.id), details=f"email_changed={email_changed};admin_changed={old_admin}->{user.is_admin}"))
        db.session.commit()
        flash('Benutzer aktualisiert.')
        return redirect(url_for('admin.index'))
    return render_template('admin/edit_user.html', user=user)

@bp.route('/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.id:
        return redirect(url_for('admin.index'))
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    db.session.add(AuditLog(actor_id=current_user.id, action='toggle_admin', target_type='user', target_id=str(user.id), details=f"new_admin={user.is_admin}"))
    db.session.commit()
    flash('Admin-Status geändert.')
    return redirect(url_for('admin.index'))

@bp.route('/user/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    from werkzeug.security import generate_password_hash
    import secrets, string
    user = User.query.get_or_404(user_id)
    alphabet = string.ascii_letters + string.digits + '!@$%&_'
    new_pw = ''.join(secrets.choice(alphabet) for _ in range(14))
    user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    # E-Mail Versand (mit einfachem Retry & Diagnose)
    from flask_mail import Message as MailMessage
    from app import mail
    status = 'fail'
    err_txt = ''
    for attempt in range(2):
        try:
            text_body = f'Dein neues temporäres Passwort lautet: {new_pw}'
            html_body = render_template('emails/reset_password.html', username=user.username, password=new_pw, portal_url=f"https://{request.host}", subject='Neues Passwort')
            msg = MailMessage(subject='Neues Passwort', sender=None, recipients=[user.email], body=text_body, html=html_body)
            mail.send(msg)
            status = 'success'
            break
        except Exception as e:
            err_txt = repr(e)
    if status == 'success':
        flash('Neues Passwort generiert und per E-Mail gesendet.')
    else:
        flash(f'Neues Passwort: {new_pw} (E-Mail Versand fehlgeschlagen)')
    details = f"email={user.email};status={status};error={err_txt[:180]}" if status!='success' else f"email={user.email};status=success"
    db.session.add(AuditLog(actor_id=current_user.id, action='reset_password', target_type='user', target_id=str(user.id), details=details))
    db.session.commit()
    return redirect(url_for('admin.index'))

@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Eigenes Konto nicht löschen.')
        return redirect(url_for('admin.index'))
    user = User.query.get_or_404(user_id)
    if user.deleted_at:
        flash('Benutzer bereits entfernt.')
        return redirect(url_for('admin.index'))
    from datetime import datetime
    # Soft Delete: Markieren + Anonymisieren (Username/Email freigeben)
    original_username = user.username
    user.deleted_at = datetime.utcnow()
    user.username = f"del_{user.id}_{int(user.deleted_at.timestamp())}"
    user.email = f"deleted_{user.id}@example.invalid"
    user.password_hash = ''
    # is_admin zurücksetzen zur Sicherheit
    user.is_admin = False
    db.session.commit()
    db.session.add(AuditLog(actor_id=current_user.id, action='soft_delete_user', target_type='user', target_id=str(user.id), details=f"orig_username={original_username}"))
    db.session.commit()
    flash('Benutzer (soft) gelöscht / anonymisiert.')
    return redirect(url_for('admin.index'))

@bp.route('/export/events.csv')
@login_required
@admin_required
def export_events_csv():
    rows = Event.query.order_by(Event.start_time.asc()).all()
    def generate():
        yield 'id;title;start;end;all_day;type;important\n'
        for e in rows:
            yield f"{e.id};{e.title};{e.start_time.isoformat()};{e.end_time.isoformat()};{int(e.all_day)};{e.event_type or ''};{int(e.is_important)}\n"
    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=events.csv'})

@bp.route('/export/audit.csv')
@login_required
@admin_required
def export_audit_csv():
    q = AuditLog.query.order_by(AuditLog.created_at.desc())
    action = request.args.get('action')
    if action:
        q = q.filter(AuditLog.action==action)
    rows = q.limit(5000).all()  # Hard cap to avoid huge downloads
    def generate():
        yield 'id;created_at;actor_id;action;target_type;target_id;details\n'
        for log in rows:
            ts = log.created_at.isoformat() if log.created_at else ''
            details = (log.details or '').replace('\n',' ').replace('\r',' ')
            yield f"{log.id};{ts};{log.actor_id};{log.action};{log.target_type};{log.target_id};{details}\n"
    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=audit_logs.csv'})

@bp.route('/system')
@login_required
@admin_required
def system_info():
    """Systeminformationen & einfache Statusanzeige.
    - Uptime
    - Stats
    - Fehler / Logs
    - Optional: Prozessressourcen (ohne psutil fallback)
    """
    import platform, os, sys, datetime, re, json
    from flask import current_app
    # Basis Stats
    stats = {
        'users_total': db.session.scalar(db.select(func.count(User.id))),
        'events_total': db.session.scalar(db.select(func.count(Event.id))),
        'messages_total': db.session.scalar(db.select(func.count(Message.id))),
        'photos_total': db.session.scalar(db.select(func.count(Photo.id)))
    }
    now = datetime.datetime.utcnow()
    uptime_seconds = (now - APP_START).total_seconds()
    # System
    # psutil optional verwenden
    memory_rss_mb = None
    pid = os.getpid()
    try:
        import psutil  # type: ignore
        process = psutil.Process(pid)
        mem = process.memory_info()
        memory_rss_mb = round(mem.rss/1024/1024,1)
    except Exception:
        # Fallback: versuche über /proc oder resource
        try:
            import resource
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            # ru_maxrss gibt KB (Linux) oder Bytes (macOS) zurück; heuristik
            maxrss = rusage.ru_maxrss
            if maxrss > 10_000_000:  # vermutlich Bytes
                memory_rss_mb = round(maxrss/1024/1024,1)
            else:  # vermutlich KB
                memory_rss_mb = round(maxrss/1024,1)
        except Exception:
            memory_rss_mb = -1  # unbekannt
    loadavg = None
    try:
        loadavg = os.getloadavg()
    except Exception:
        pass
    py_impl = platform.python_implementation()
    sysinfo = {
        'python': sys.version.split('\n')[0],
        'python_impl': py_impl,
        'platform': platform.platform(),
        'process_pid': pid,
        'memory_rss_mb': memory_rss_mb,
        'uptime_h': round(uptime_seconds/3600,2),
        'loadavg': loadavg,
        'cwd': os.getcwd(),
        'executable': sys.executable,
        'psutil_available': memory_rss_mb not in (-1, None)
    }
    # Fehlersuche in AuditLog (heuristisch: status=fail oder 'error=' in details)
    error_logs = AuditLog.query.filter(
        AuditLog.details.ilike('%status=fail%') | AuditLog.details.ilike('%error=%')
    ).order_by(AuditLog.created_at.desc()).limit(30).all()
    # Logdatei parsen (letzte 400 Zeilen, filtern auf ERROR|WARNING)
    log_entries = []
    log_path = current_app.config.get('LOG_FILE')
    if log_path and os.path.isfile(log_path):
        try:
            with open(log_path, 'rb') as fh:
                # Tail effizient
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                block = 8192
                data = b''
                while len(data.splitlines()) < 450 and size > 0:
                    seek = max(size - block, 0)
                    fh.seek(seek)
                    data = fh.read(size - seek) + data
                    size = seek
                lines = data.decode(errors='replace').splitlines()[-450:]
            pattern = re.compile(r'(ERROR|WARNING|TRACEBACK)', re.IGNORECASE)
            for ln in lines:
                if pattern.search(ln):
                    log_entries.append(ln[-500:])
        except Exception as e:
            log_entries.append(f"<Fehler beim Lesen der Logdatei: {e!r}>")
    # Health Flags
    warnings = []
    if isinstance(sysinfo['memory_rss_mb'], (int,float)) and sysinfo['memory_rss_mb'] not in (-1, None) and sysinfo['memory_rss_mb'] > 500:
        warnings.append(f"Speichernutzung hoch: {sysinfo['memory_rss_mb']} MB")
    if sysinfo['loadavg'] and sysinfo['loadavg'][0] > 4:
        warnings.append(f"Load hoch: {sysinfo['loadavg'][0]:.2f}")
    return render_template('admin/system.html', stats=stats, sysinfo=sysinfo, error_logs=error_logs, log_entries=log_entries, warnings=warnings)

@bp.route('/system/mail-check', methods=['POST'])
@login_required
@admin_required
def system_mail_check():
    """Versendet eine Test-Mail an aktuellen Admin Benutzer."""
    from flask_mail import Message as MailMessage
    from app import mail
    import datetime
    status = 'fail'; err=''
    try:
        msg = MailMessage(subject='Mail Health Check', recipients=[current_user.email], body=f'Testmail {datetime.datetime.utcnow().isoformat()}')
        mail.send(msg)
        status='ok'
    except Exception as e:
        err=repr(e)
    db.session.add(AuditLog(actor_id=current_user.id, action='mail_health', target_type='system', target_id='mail', details=f'status={status};error={err[:160]}'))
    db.session.commit()
    flash('Mail Health: ' + (status.upper() if status=='ok' else f'FEHLER ({err[:80]})'))
    return redirect(url_for('admin.system_info'))

@bp.route('/user/new', methods=['GET','POST'])
@login_required
@admin_required
def new_user():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip().lower()
        is_admin_flag = bool(request.form.get('is_admin'))
        errors = []
        if not username:
            errors.append('Username erforderlich')
        if not email:
            errors.append('E-Mail erforderlich')
        if User.query.filter_by(username=username).first():
            errors.append('Username bereits vergeben')
        if User.query.filter_by(email=email).first():
            errors.append('E-Mail bereits vergeben')
        if errors:
            for e in errors: flash(e)
            return render_template('admin/new_user.html', form_data={'username':username,'email':email,'is_admin':is_admin_flag})
        # Passwort generieren
        import secrets, string
        alphabet = string.ascii_letters + string.digits + '!@$%&_'
        password = ''.join(secrets.choice(alphabet) for _ in range(14))
        user = User(username=username, email=email, is_admin=is_admin_flag)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        # E-Mail mit Zugangsdaten (Retry + Diagnose)
        from flask_mail import Message as MailMessage
        from app import mail
        text_body = (f"Hallo {username},\n\n"
                     f"Ein Account wurde für dich angelegt.\n\n"
                     f"Login: {email}\nPasswort (bitte nach erstem Login ändern): {password}\n\n"
                     f"URL: https://{request.host}\n\nViele Grüße")
        html_body = render_template('emails/new_user.html', username=username, email=email, password=password, portal_url=f"https://{request.host}", subject='Dein Zugang')
        mail_status='fail'; mail_err=''
        for attempt in range(2):
            try:
                msg = MailMessage(subject='Dein Zugang', sender=None, recipients=[email], body=text_body, html=html_body)
                mail.send(msg)
                mail_status='success'
                break
            except Exception as e:
                mail_err=repr(e)
        if mail_status=='success':
            flash('Benutzer erstellt und E-Mail gesendet.')
        else:
            flash(f'Benutzer erstellt. Passwort: {password} (E-Mail Versand fehlgeschlagen)')
        details = f"username={username};email={email};admin={is_admin_flag};mail_status={mail_status}" + (f";error={mail_err[:180]}" if mail_status!='success' else '')
        db.session.add(AuditLog(actor_id=current_user.id, action='create_user', target_type='user', target_id=str(user.id), details=details))
        db.session.commit()
        return redirect(url_for('admin.index'))
    return render_template('admin/new_user.html')
