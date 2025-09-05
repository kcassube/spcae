from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))  # verlängert für scrypt/andere lange Hashes
    is_admin = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, index=True)  # Soft Delete (statt physischem Löschen)
    
    # Beziehungen
    events = db.relationship('Event', backref='author', lazy='dynamic')
    expenses = db.relationship('Expense', backref='user', lazy='dynamic')
    photos = db.relationship('Photo', backref='user', lazy='dynamic')
    messages_sent = db.relationship('Message',
                                  foreign_keys='Message.sender_id',
                                  backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message',
                                      foreign_keys='Message.recipient_id',
                                      backref='recipient', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    color = db.Column(db.String(20))  # Für die Ereignisfarbe
    all_day = db.Column(db.Boolean, default=False)
    reminder = db.Column(db.Boolean, default=False)
    reminder_time = db.Column(db.Integer)  # Minuten vor dem Ereignis
    event_type = db.Column(db.String(20), index=True, default='default')  # z.B. 'default','birthday','important'
    is_important = db.Column(db.Boolean, default=False)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence = db.Column(db.String(50))  # z.B. 'annual'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    color = db.Column(db.String(20))
    monthly_budget = db.Column(db.Float())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime())
    # NEU: Typ (expense | income | both)
    category_type = db.Column(db.String(10), default='expense', index=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    kind = db.Column(db.String(20), default='expense', index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    # NEU:
    payment_method = db.Column(db.String(30))
    notes = db.Column(db.Text())
    # Konto-Verknüpfung (optional für ältere Daten leer). Bei income wird Betrag gutgeschrieben, bei expense abgezogen.
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), index=True)

class RecurringTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    kind = db.Column(db.String(20), default='expense')  # income/expense
    category = db.Column(db.String(64), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    start_date = db.Column(db.Date, nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # monthly, weekly, yearly
    last_generated_date = db.Column(db.Date)  # letzte erzeugte Instanz
    active = db.Column(db.Boolean, default=True, index=True)
    # Konto für automatisch generierte Buchungen
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), index=True)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), index=True, default=1)
    archived_at = db.Column(db.DateTime, index=True)

class ChatRoom(db.Model):
    __tablename__ = 'chat_rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_message_at = db.Column(db.DateTime, index=True)
    # Neu: Admin-only Räume (werden normalen Usern ausgeblendet)
    is_admin_only = db.Column(db.Boolean, default=False, index=True)

class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    title = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    bio = db.Column(db.Text)
    avatar_filename = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notification_prefs = db.Column(db.String(500))  # JSON-ähnliche kommagetrennte Liste (vereinfachtes Speichern)

class NotificationPreference(db.Model):
    __tablename__ = 'notification_preferences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    channel = db.Column(db.String(20), nullable=False)  # email, socket
    kind = db.Column(db.String(30), nullable=False)  # events, finance, chat, photos, system
    enabled = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id','channel','kind', name='uq_pref_user_channel_kind'),)

class NotificationEvent(db.Model):
    __tablename__ = 'notification_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)
    channel = db.Column(db.String(20), nullable=False)
    payload = db.Column(db.Text)  # JSON Payload
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    delivered = db.Column(db.Boolean, default=False, index=True)
    delivered_at = db.Column(db.DateTime)

class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_used_at = db.Column(db.DateTime)

def get_or_create_profile(user):
    """Liefert das UserProfile des Users oder legt es an."""
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return profile

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(120), nullable=False)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.String(50))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# ---- Finanz-Konten ----
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    account_type = db.Column(db.String(50), nullable=False, default='Girokonto')  # Girokonto, Sparkonto, Kreditkarte, etc.
    balance = db.Column(db.Float, nullable=False, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # optional Besitzer, None = geteilt
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    # Darf Konto ins Minus gehen?
    allow_negative = db.Column(db.Boolean, nullable=False, default=False, index=True)
    # Zusätzliche Felder für erweiterte Kontoverwaltung
    bank_name = db.Column(db.String(100))  # Name der Bank
    iban = db.Column(db.String(34))  # IBAN für Überweisungen
    notes = db.Column(db.Text)  # Notizen zum Konto

class AccountTransaction(db.Model):
    __tablename__ = 'account_transactions'
    id = db.Column(db.Integer, primary_key=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    to_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    amount = db.Column(db.Float, nullable=False)  # positiver Betrag
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class AccountBalanceSnapshot(db.Model):
    __tablename__ = 'account_balance_snapshot'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)
    day = db.Column(db.Date, nullable=False, index=True)
    balance = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('account_id','day', name='uq_snapshot_account_day'),)

class Budget(db.Model):
    """Budget-Verwaltung pro Kategorie und Monat"""
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_name = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    planned_amount = db.Column(db.Float, nullable=False, default=0.0)
    actual_amount = db.Column(db.Float, nullable=False, default=0.0)  # Wird automatisch berechnet
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('category_name', 'user_id', 'year', 'month', name='uq_budget_cat_user_month'),)

class FinancialGoal(db.Model):
    """Finanzielle Ziele und Sparziele"""
    __tablename__ = 'financial_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    target_date = db.Column(db.Date)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))  # Konto für das Sparziel
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
