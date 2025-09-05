from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app.calendar import bp
from app.models import Event
from app import db, mail
from flask_mail import Message
import requests
from datetime import datetime, timedelta
from flask import current_app

def _send_event_email(template, subject, user, **context):
    try:
        html_body = render_template(template, username=user.username, portal_url=f"https://{request.host}", **context, subject=subject)
        text_body = f"{subject}\nBitte im Portal ansehen."
        msg = Message(subject=subject, recipients=[user.email], body=text_body, html=html_body)
        mail.send(msg)
    except Exception:
        # Leise scheitern (könnte später AuditLog bekommen)
        pass

@bp.route('/')
@login_required
def index():
    return render_template('calendar/index.html')

@bp.route('/events')
@login_required
def get_events():
    """Event Feed.
    Verbesserungen:
      - Zeitzonen-normalisierung (vergleiche naive Datetimes)
      - Geburtstage/Jahres-Events werden für benötigte Jahre expandiert
      - Optionaler Parameter scope=mine|all (default: all) für Familien-Kalender
    """
    start_param = request.args.get('start')
    end_param = request.args.get('end')
    try:
        view_start = datetime.fromisoformat(start_param.replace('Z', '+00:00')) if start_param else datetime.utcnow() - timedelta(days=30)
        view_end = datetime.fromisoformat(end_param.replace('Z', '+00:00')) if end_param else datetime.utcnow() + timedelta(days=60)
    except Exception:
        view_start = datetime.utcnow() - timedelta(days=30)
        view_end = datetime.utcnow() + timedelta(days=60)
    # TZ -> naive
    if view_start.tzinfo:
        view_start = view_start.replace(tzinfo=None)
    if view_end.tzinfo:
        view_end = view_end.replace(tzinfo=None)

    scope = request.args.get('scope','all')
    if scope == 'mine':
        events = Event.query.filter_by(user_id=current_user.id).all()
    else:
        events = Event.query.all()
    out = []

    for event in events:
        base_color = event.color
        # Standardfarben je Typ (falls keine gesetzt)
        if not base_color:
            if event.event_type == 'birthday':
                base_color = '#ffb347'  # orange/pastell
            elif event.event_type == 'important' or event.is_important:
                base_color = '#ff4d4f'  # rot
            else:
                base_color = '#3788d8'

        title = event.title
        if event.event_type == 'birthday':
            if '🎂' not in title:
                title = '🎂 ' + title
        elif event.is_important:
            if '⭐' not in title:
                title = '⭐ ' + title

        def serialize(e_start, e_end, instance_suffix=None):
            ev_id = f"{event.id}-{instance_suffix}" if instance_suffix else str(event.id)
            # Für Ganztags-Events nur Datum liefern, dadurch kein TZ-Shift
            if event.all_day or event.event_type == 'birthday':
                start_out = e_start.date().isoformat()
                # FullCalendar interpretiert end exklusiv -> +1 Tag setzen
                end_out = (e_start.date() + timedelta(days=1)).isoformat()
            else:
                start_out = e_start.isoformat()
                end_out = e_end.isoformat()
            payload = {
                'id': ev_id,
                'originalId': event.id,
                'title': title,
                'start': start_out,
                'description': event.description,
                'allDay': True if (event.all_day or event.event_type == 'birthday') else False,
                'color': base_color,
                'backgroundColor': base_color,
                'borderColor': base_color,
                'eventType': event.event_type,
                'important': event.is_important,
                'recurring': True if event.event_type == 'birthday' else event.is_recurring,
                'recurrence': 'annual' if event.event_type == 'birthday' else event.recurrence,
                'isInstance': True if instance_suffix else False
            }
            if end_out:
                payload['end'] = end_out
            return payload

        # Geburtstage oder explizit jährliche Events expandieren
        if event.event_type == 'birthday' or (event.is_recurring and event.recurrence == 'annual'):
            # Nur benötigte Jahre: von view_start.year bis view_end.year (plus Sicherheitsrand 1 Jahr).
            years_needed = range(view_start.year - 1, view_end.year + 1)
            for y in years_needed:
                try:
                    new_start = event.start_time.replace(year=y)
                    new_end = event.end_time.replace(year=y)
                except ValueError:
                    if event.start_time.month == 2 and event.start_time.day == 29:  # Leap Day -> 28.
                        new_start = event.start_time.replace(year=y, day=28)
                        new_end = event.end_time.replace(year=y, day=28)
                    else:
                        continue
                # Vergleiche nur Datum, da Geburtstage all-day sind
                if new_end.date() < view_start.date() or new_start.date() > view_end.date():
                    continue
                out.append(serialize(new_start, new_end, instance_suffix=y))
        else:
            out.append(serialize(event.start_time, event.end_time))

    # Debug Info optional
    if request.args.get('debug') == '1':
        meta = {
            'count': len(out),
            'view_start': view_start.isoformat(),
            'view_end': view_end.isoformat(),
            'raw_events': len(events)
        }
        return jsonify({'events': out, 'meta': meta})
    return jsonify(out)

@bp.route('/event', methods=['POST','PUT'])
@login_required
def create_or_update_event():
    data = request.get_json()
    if request.method == 'PUT':
        event_id = data.get('id')
        event = Event.query.get_or_404(event_id)
        if event.user_id != current_user.id:
            return jsonify({'error':'Unauthorized'}),403
        old_snapshot = {
            'title': event.title,
            'start_time': event.start_time,
            'end_time': event.end_time,
            'description': event.description,
            'color': event.color,
            'all_day': event.all_day,
            'event_type': event.event_type,
            'is_important': event.is_important
        }
    else:
        event = Event(user_id=current_user.id)
        old_snapshot = None

    # Basisfelder
    event.title = data.get('title','').strip()
    if not event.title:
        return jsonify({'error':'Titel erforderlich'}), 400
    event.description = data.get('description','')
    # Support für ganztägige & lokale Zeiten
    start_str = data.get('start')
    if not start_str:
        return jsonify({'error':'Startzeit/Datum fehlt'}), 400
    end_str = data.get('end', start_str)
    event.all_day = bool(data.get('allDay')) or data.get('eventType') == 'birthday'
    if event.all_day:
        # Falls nur Datum gesendet wurde (YYYY-MM-DD)
        if len(start_str) == 10:
            event.start_time = datetime.fromisoformat(start_str + 'T12:00:00')  # Mittags setzen um TZ-Shift zu vermeiden
        else:
            event.start_time = datetime.fromisoformat(start_str[0:10] + 'T12:00:00')
        # Endzeit intern identisch oder +12h ist egal für allDay; wir spiegeln Start
        event.end_time = event.start_time
    else:
        event.start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        event.end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    event.color = data.get('color')
    event.reminder = bool(data.get('reminder'))
    event.reminder_time = data.get('reminderTime')
    incoming_type = data.get('eventType')
    if incoming_type:  # Nur überschreiben, wenn gesendet
        event.event_type = incoming_type
    elif not event.event_type:  # Initialfall
        event.event_type = 'default'
    event.is_important = bool(data.get('important'))
    # Geburtstage immer jährlich wiederkehrend kennzeichnen
    if event.event_type == 'birthday':
        event.is_recurring = True
        event.recurrence = 'annual'
    else:
        event.is_recurring = bool(data.get('recurring'))
        event.recurrence = data.get('recurrence')

    if request.method == 'POST':
        db.session.add(event)
    db.session.commit()
    # E-Mail Benachrichtigung
    if old_snapshot is None:
        _send_event_email('emails/event_created.html', 'Neues Ereignis', current_user, event=event)
    else:
        changes = []
        if event.title != old_snapshot['title']: changes.append('Titel')
        if event.start_time != old_snapshot['start_time'] or event.end_time != old_snapshot['end_time']: changes.append('Zeit')
        if event.description != old_snapshot['description']: changes.append('Beschreibung')
        if event.color != old_snapshot['color']: changes.append('Farbe')
        if event.all_day != old_snapshot['all_day']: changes.append('Ganztägig')
        if event.event_type != old_snapshot['event_type']: changes.append('Typ')
        if event.is_important != old_snapshot['is_important']: changes.append('Wichtigkeit')
        if changes:
            _send_event_email('emails/event_updated.html', 'Ereignis aktualisiert', current_user, event=event, changes=", ".join(changes))
    
    return jsonify({
        'id': event.id,
        'title': event.title,
        'start': event.start_time.isoformat(),
        'end': event.end_time.isoformat(),
        'description': event.description,
        'allDay': event.all_day,
        'color': event.color,
        'eventType': event.event_type,
        'important': event.is_important,
        'recurring': event.is_recurring,
        'recurrence': event.recurrence
    })

@bp.route('/event/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    title = event.title
    db.session.delete(event)
    db.session.commit()
    _send_event_email('emails/event_deleted.html', 'Ereignis gelöscht', current_user, title=title)
    return jsonify({'status': 'success'})

@bp.route('/horoscope/<sign>')
@login_required
def get_horoscope(sign):
    # Hier würden wir normalerweise eine echte Horoskop-API verwenden
    # Für Demonstrationszwecke verwenden wir statische Antworten
    horoscopes = {
        'aries': 'Ein spannender Tag erwartet Sie. Neue Möglichkeiten eröffnen sich.',
        'taurus': 'Heute ist ein guter Tag für wichtige Entscheidungen.',
        'gemini': 'Ihre Kommunikationsfähigkeiten sind heute besonders stark.',
        'cancer': 'Familie steht heute im Mittelpunkt. Planen Sie etwas Besonderes.',
        'leo': 'Ihre kreative Energie ist heute besonders hoch.',
        'virgo': 'Ein guter Tag für Organisation und Planung.',
        'libra': 'Harmonie und Balance sind heute wichtige Themen.',
        'scorpio': 'Intuition wird Sie heute gut leiten.',
        'sagittarius': 'Abenteuer und neue Erfahrungen warten auf Sie.',
        'capricorn': 'Fokussieren Sie sich auf Ihre Ziele.',
        'aquarius': 'Innovative Ideen führen zum Erfolg.',
        'pisces': 'Ihre künstlerische Seite möchte sich ausdrücken.'
    }
    
    return jsonify({
        'sign': sign,
        'horoscope': horoscopes.get(sign, 'Horoskop nicht verfügbar.')
    })
