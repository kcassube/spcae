import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-this'
    # Version für statische Assets (Cache-Busting). Bei Frontend-Änderungen hochzählen.
    ASSET_VERSION = os.environ.get('ASSET_VERSION', '2025-09-04-4')
    # Template Auto Reload (auch in Production zurzeit erwünscht wegen schneller Iteration)
    TEMPLATES_AUTO_RELOAD = True
    _raw_db_uri = os.environ.get('DATABASE_URL')
    if _raw_db_uri and _raw_db_uri.startswith('mysql://'):
        # Falls jemand mysql:// statt mysql+pymysql:// nutzt, ergänzen
        _raw_db_uri = _raw_db_uri.replace('mysql://','mysql+pymysql://',1)
    if not _raw_db_uri:
        _raw_db_uri = 'mysql+pymysql://family_portal:Paha1237!@localhost/family_portal'
    # Charset sicherstellen
    if _raw_db_uri.startswith('mysql+') and 'charset=' not in _raw_db_uri:
        sep = '&' if '?' in _raw_db_uri else '?'
        _raw_db_uri = f"{_raw_db_uri}{sep}charset=utf8mb4"
    SQLALCHEMY_DATABASE_URI = _raw_db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Konfiguration
    # Upload Ziel (wird in create_app nochmal harmonisiert und ggf. auf instance/uploads gesetzt)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_DIR') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # Mail Konfiguration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    # Robuste Boolean-Auswertung (MAIL_USE_TLS=0 deaktiviert TLS explizit)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', '1').lower() in ('1','true','yes','on')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    ADMINS = ['admin@dchome.app']
    # Pfad zur Applikations Logdatei (optional), kann via ENV überschrieben werden
    LOG_FILE = os.environ.get('APP_LOG_FILE') or '/var/log/family_portal/app.log'
    # Web Push konfiguration
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or ''
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or ''
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL') or 'admin@dchome.app'
    ENABLE_WEB_PUSH = True
    # Finance Module entfernt – FINANCE_FAMILY_SHARED nicht mehr genutzt
