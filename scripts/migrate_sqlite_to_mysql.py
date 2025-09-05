import os
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from getpass import getpass

# Config
SQLITE_PATH = os.path.join('instance','family_portal.db')  # existing sqlite file
MYSQL_URL = os.environ.get('MYSQL_URL') or os.environ.get('DATABASE_URL')
if not MYSQL_URL or MYSQL_URL.startswith('sqlite:'):
    # fallback hardcode (adjust if needed)
    MYSQL_URL = 'mysql+pymysql://family_portal:Paha1237!@localhost/family_portal'

print(f"SQLite: {SQLITE_PATH}")
print(f"MySQL:  {MYSQL_URL}")

if not os.path.exists(SQLITE_PATH):
    raise SystemExit('SQLite Datei nicht gefunden.')

sqlite_engine = create_engine(f'sqlite:///{SQLITE_PATH}')
mysql_engine = create_engine(MYSQL_URL)

SqlSession = sessionmaker(bind=sqlite_engine)
MySession = sessionmaker(bind=mysql_engine)

src_session = SqlSession()
dst_session = MySession()

meta_sqlite = MetaData()
meta_mysql = MetaData()

TABLES = ['user','event','expense','message','photo']
for t in TABLES:
    Table(t, meta_sqlite, autoload_with=sqlite_engine)
    Table(t, meta_mysql, autoload_with=mysql_engine)

# Reihenfolge beachten wegen FK (user -> event etc.)
order = ['user','event','expense','message','photo']

copied = {}
for name in order:
    src_table = meta_sqlite.tables[name]
    dst_table = meta_mysql.tables[name]
    rows = list(src_session.execute(src_table.select()))
    if not rows:
        copied[name] = 0
        continue
    # Insert bulk
    data = []
    for r in rows:
        d = dict(r._mapping)
        # Feldlängen anpassen
        if name == 'user' and 'password_hash' in d and d['password_hash'] and len(d['password_hash']) > 256:
            d['password_hash'] = d['password_hash'][:256]
        data.append(d)
    if data:
        dst_session.execute(dst_table.insert(), data)
        copied[name] = len(data)
        print(f"Übertragen: {name} -> {len(data)} Sätze")

# Commit
try:
    dst_session.commit()
except Exception as e:
    dst_session.rollback()
    raise
finally:
    src_session.close()
    dst_session.close()

print('Fertig. Zusammenfassung:')
for k,v in copied.items():
    print(f"  {k}: {v}")
