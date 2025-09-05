from flask import Flask
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from config import Config
import os
import logging
from logging.handlers import RotatingFileHandler

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
# Verwende einfachen Threading-Modus (kein eventlet/gevent nötig)
socketio = SocketIO(async_mode='threading')
csrf = CSRFProtect()

# App Startzeitpunkt (für Systeminfo/Uptime)
APP_START = datetime.utcnow()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # (Hinweis) Socket.IO Client wird jetzt fest im Repository ausgeliefert (app/static/js/socket.io.full.min.js)
    
    app.config.setdefault('UPLOAD_BASE', os.path.join(app.instance_path, 'uploads'))
    # Rückwärtskompatibilität: Falls Code noch UPLOAD_FOLDER liest
    app.config.setdefault('UPLOAD_FOLDER', app.config['UPLOAD_BASE'])
    # instance + uploads basis sicherstellen (Best-Effort)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(app.config['UPLOAD_BASE'], exist_ok=True)
    except Exception:
        pass
    
    # Initialisiere Erweiterungen
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    socketio.init_app(app)
    csrf.init_app(app)
    
    login_manager.login_view = 'auth.login'
    
    # Registriere Blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    # Push API Blueprint
    from app.main.push import bp_push as push_bp
    app.register_blueprint(push_bp)
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.calendar import bp as calendar_bp
    app.register_blueprint(calendar_bp, url_prefix='/calendar')
    
    # Finance-Modul entfernt (Blueprints wurden ausgebaut)
    
    from app.chat import bp as chat_bp
    from app.photos import bp as photos_bp
    from app.profile import bp as profile_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(photos_bp, url_prefix='/photos')
    app.register_blueprint(profile_bp, url_prefix='/profile')

    # Socket.IO Event Handler laden
    from . import socket_handlers  # noqa: F401

    # Context Processor für Asset-Version (Cache Busting)
    @app.context_processor
    def inject_asset_version():
        return { 'static_version': app.config.get('ASSET_VERSION', '1') }

    # Root-Scope Service Worker Bereitstellung, damit Push-Status auf allen Seiten ermittelbar ist.
    @app.route('/sw.js')
    def service_worker():  # pragma: no cover - trivial static proxy
        # Datei liegt physisch unter static/js/sw.js
        return app.send_static_file('js/sw.js')
    
    # Logging Setup (einmalig)
    _setup_logging(app)
    return app

def _setup_logging(app: Flask):
    """Initialisiert File Logging (Rotating) und optional E-Mail Fehlerlogging.
    Wird idempotent ausgeführt (mehrfacher Aufruf erzeugt keine doppelten Handler)."""
    if app.logger.handlers and any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        return
    log_file = app.config.get('LOG_FILE')
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.info('File Logging initialisiert')
        except Exception as e:
            app.logger.error('Konnte Logdatei nicht initialisieren: %r', e)
    # Fehlerlevel
    app.logger.setLevel(logging.INFO)
