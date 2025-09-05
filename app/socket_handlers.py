from flask_login import current_user
from flask import request, current_app
from app import socketio
from flask_socketio import join_room
from app.models import NotificationPreference, NotificationEvent, PushSubscription
from app import db, mail
from datetime import datetime
from flask_mail import Message as MailMessage

# Namespace optional: default

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # Privaten Raum betreten
        join_room(f'user_{current_user.id}')
        print(f"[socket] connect user={current_user.id} sid={request.sid}")
    else:
        # Gäste abweisen? (optional disconnect)
        print(f"[socket] connect guest sid={request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    # Räume werden automatisch verlassen
    pass


def notify_user(user_id:int, kind:str, payload:dict, channels=None):
    """Versendet eine Benachrichtigung.
    Regeln:
      - Wenn keine Präferenzen existieren -> socket als Default aktiv, E-Mail nur Opt-In.
      - Explizit deaktivierte Präferenz blockt Kanal.
      - Wenn Push Subscriptions existieren und 'socket' angefordert wurde, wird 'push' ergänzt.
    Rückgabe: dict mit Status pro Kanal.
    """
    import json
    if channels is None:
        channels = ['email','socket']
    result = {}
    try:
        all_prefs = NotificationPreference.query.filter_by(user_id=user_id, kind=kind).all()
        if not all_prefs:
            enabled_channels = {'socket'} & set(channels)
        else:
            enabled_channels = {p.channel for p in all_prefs if p.enabled and p.channel in channels}
        if 'socket' in channels and PushSubscription.query.filter_by(user_id=user_id).count() > 0:
            enabled_channels.add('push')
        if not enabled_channels:
            return {'skipped':'no-enabled-channels'}
        now = datetime.utcnow()
        for ch in enabled_channels:
            ev = NotificationEvent(user_id=user_id, kind=kind, channel=ch, payload=json.dumps(payload), created_at=now)
            db.session.add(ev)
            if ch == 'socket':
                socketio.emit('notification', { 'kind': kind, 'payload': payload }, room=f'user_{user_id}')
                ev.delivered = True; ev.delivered_at = datetime.utcnow()
                result['socket']='sent'
            elif ch == 'push':
                from pywebpush import webpush, WebPushException
                subs = PushSubscription.query.filter_by(user_id=user_id).all()
                data = json.dumps({'title': f'Neue {kind}', 'body': payload.get('message') or payload.get('title') or kind, 'url':'/'})
                priv = current_app.config.get('VAPID_PRIVATE_KEY')
                pub = current_app.config.get('VAPID_PUBLIC_KEY')
                claim = current_app.config.get('VAPID_CLAIM_EMAIL')
                sent=0; errors=0
                if priv and pub:
                    for s in subs:
                        try:
                            webpush(subscription_info={'endpoint': s.endpoint,'keys':{'p256dh':s.p256dh,'auth':s.auth}}, data=data, vapid_private_key=priv, vapid_claims={'sub':f'mailto:{claim}'})
                            sent+=1
                        except WebPushException:
                            errors+=1
                result['push']=f'sent:{sent}/err:{errors}'
            elif ch == 'email':
                # Einfache Mail (fail-silent in Result vermerken)
                try:
                    subject = payload.get('subject') or f'Neue Benachrichtigung: {kind}'
                    body = payload.get('message') or payload.get('title') or json.dumps(payload)[:400]
                    from app.models import User
                    user = User.query.get(user_id)
                    if user and user.email:
                        msg = MailMessage(subject=subject, recipients=[user.email], body=body)
                        mail.send(msg)
                        ev.delivered = True; ev.delivered_at = datetime.utcnow()
                        result['email']='sent'
                    else:
                        result['email']='no-address'
                except Exception as e:
                    result['email']=f'error:{e.__class__.__name__}'
        db.session.commit()
    except Exception as outer:
        db.session.rollback()
        result['error']=repr(outer)
    return result
