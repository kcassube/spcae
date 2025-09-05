from flask import render_template
from app.main import bp
from flask_login import current_user, login_required
from datetime import datetime, date, timedelta
from app import db
from app.models import Event, ChatMessage, Photo

@bp.route('/')
def index():
    if current_user.is_anonymous:
        return render_template('index.html', title='Willkommen')

    today = date.today()
    now = datetime.now()
    
    # Events: nächste 7 Tage
    upcoming = Event.query.filter(Event.start_time >= datetime.utcnow(),
                                   Event.start_time <= datetime.utcnow()+timedelta(days=7),
                                   Event.user_id==current_user.id)
    upcoming = upcoming.order_by(Event.start_time.asc()).limit(5).all()

    # Finance entfernt: keine Berechnung von incomes/expenses/balance/top_categories
    incomes = expenses = balance = 0.0
    top_categories = []

    # Chat: letzte 5 Nachrichten
    chat_rows = ChatMessage.query.order_by(ChatMessage.id.desc()).limit(5).all()[::-1]

    # Fotos: letzte 6
    photos = Photo.query.filter_by(user_id=current_user.id).order_by(Photo.created_at.desc()).limit(6).all()

    return render_template('index.html',
        title='Übersicht',
        now=now,
        upcoming_events=upcoming,
    # Finance Variablen entfernt
        chat_rows=chat_rows,
        photos=photos
    )
