from flask import Blueprint, current_app, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import PushSubscription
from datetime import datetime
import json

bp_push = Blueprint('pushapi', __name__)

@bp_push.route('/push/vapid_public')
@login_required
def vapid_public():
    return jsonify({'publicKey': current_app.config.get('VAPID_PUBLIC_KEY','')})

@bp_push.route('/push/subscribe', methods=['POST'])
@login_required
def subscribe():
    data = request.get_json() or {}
    endpoint = data.get('endpoint')
    keys = data.get('keys') or {}
    if not endpoint or 'p256dh' not in keys or 'auth' not in keys:
        return jsonify({'error':'invalid subscription'}),400
    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if not sub:
        sub = PushSubscription(user_id=current_user.id, endpoint=endpoint, p256dh=keys['p256dh'], auth=keys['auth'])
        db.session.add(sub)
    else:
        sub.user_id = current_user.id
        sub.p256dh = keys['p256dh']
        sub.auth = keys['auth']
        sub.last_used_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status':'ok'})

@bp_push.route('/push/test', methods=['POST'])
@login_required
def test_push():
    # send simple push to current user
    from pywebpush import webpush, WebPushException
    subs = PushSubscription.query.filter_by(user_id=current_user.id).all()
    sent = 0
    errors = []
    payload = json.dumps({'title':'Test Push','body':'Hallo von Family Portal','url':'/'})
    vapid_private = current_app.config.get('VAPID_PRIVATE_KEY')
    vapid_public = current_app.config.get('VAPID_PUBLIC_KEY')
    claim_email = current_app.config.get('VAPID_CLAIM_EMAIL')
    if not vapid_private or not vapid_public:
        return jsonify({'error':'VAPID keys missing'}),500
    for s in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': s.endpoint,
                    'keys': {'p256dh': s.p256dh, 'auth': s.auth}
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims={'sub': f'mailto:{claim_email}'}
            )
            s.last_used_at = datetime.utcnow()
            sent +=1
        except WebPushException as e:
            errors.append(str(e))
    db.session.commit()
    return jsonify({'sent':sent,'errors':errors})
