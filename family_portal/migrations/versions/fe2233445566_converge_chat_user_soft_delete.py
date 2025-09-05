"""Converge schema: ensure chat & user soft delete columns exist

Revision ID: fe2233445566
Revises: de11fe22aa44
Create Date: 2025-09-05 14:20:00.000000

Diese Migration ist idempotent. Sie fügt nur fehlende Spalten / Indizes hinzu
(für Chat Rooms, Chat Messages und User Soft Delete), damit
user-soft-delete & Chat-Räume zuverlässig funktionieren – unabhängig davon,
ob frühere Migrationen (f011..., f122...) erfolgreich liefen.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = 'fe2233445566'
down_revision = 'de11fe22aa44'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    # --- chat_rooms ---
    if 'chat_rooms' in tables:
        cols = {c['name'] for c in insp.get_columns('chat_rooms')}
        idxs = {ix['name'] for ix in insp.get_indexes('chat_rooms')}
        # last_message_at
        if 'last_message_at' not in cols:
            op.add_column('chat_rooms', sa.Column('last_message_at', sa.DateTime(), nullable=True))
        if 'ix_chat_rooms_last_message_at' not in idxs and 'last_message_at' in ({c['name'] for c in insp.get_columns('chat_rooms')}):
            op.create_index('ix_chat_rooms_last_message_at', 'chat_rooms', ['last_message_at'])
        # is_admin_only
        if 'is_admin_only' not in cols:
            op.add_column('chat_rooms', sa.Column('is_admin_only', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        # Index für is_admin_only (Model hat index=True; DB-seitig sicherstellen)
        idxs = {ix['name'] for ix in insp.get_indexes('chat_rooms')}
        if 'ix_chat_rooms_is_admin_only' not in idxs and 'is_admin_only' in ({c['name'] for c in insp.get_columns('chat_rooms')}):
            op.create_index('ix_chat_rooms_is_admin_only', 'chat_rooms', ['is_admin_only'])
        # created_at index (falls früher fehlte)
        if 'ix_chat_rooms_created_at' not in idxs and 'created_at' in cols:
            op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])
    else:
        # Table komplett anlegen (sollte selten passieren)
        op.create_table(
            'chat_rooms',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(80), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id')),
            sa.Column('last_message_at', sa.DateTime()),
            sa.Column('is_admin_only', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )
        op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])
        op.create_index('ix_chat_rooms_last_message_at', 'chat_rooms', ['last_message_at'])
        op.create_index('ix_chat_rooms_is_admin_only', 'chat_rooms', ['is_admin_only'])

    # --- chat_messages ---
    if 'chat_messages' in tables:
        cols = {c['name'] for c in insp.get_columns('chat_messages')}
        idxs = {ix['name'] for ix in insp.get_indexes('chat_messages')}
        if 'room_id' not in cols:
            op.add_column('chat_messages', sa.Column('room_id', sa.Integer(), sa.ForeignKey('chat_rooms.id'), nullable=True))
        if 'archived_at' not in cols:
            op.add_column('chat_messages', sa.Column('archived_at', sa.DateTime(), nullable=True))
        # Indizes
        idxs = {ix['name'] for ix in insp.get_indexes('chat_messages')}
        # Kombi room_id,id
        if 'ix_chat_messages_room_id_id' not in idxs and {'room_id','id'}.issubset({c['name'] for c in insp.get_columns('chat_messages')}):
            op.create_index('ix_chat_messages_room_id_id', 'chat_messages', ['room_id','id'])
        if 'ix_chat_messages_archived_at' not in idxs and 'archived_at' in ({c['name'] for c in insp.get_columns('chat_messages')}):
            op.create_index('ix_chat_messages_archived_at', 'chat_messages', ['archived_at'])
        # Backfill Standard-Raum falls notwendig
        try:
            # Standard-Raum sicherstellen
            res = bind.execute(text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()
            if not res:
                bind.execute(text("INSERT INTO chat_rooms (name) VALUES (:n)"), {"n": 'Allgemein'})
                res = bind.execute(text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()
            default_room_id = res[0]
            if 'room_id' in ({c['name'] for c in insp.get_columns('chat_messages')}):
                bind.execute(text("UPDATE chat_messages SET room_id=:rid WHERE room_id IS NULL"), {"rid": default_room_id})
        except Exception:
            pass
    # else: Tabelle nicht vorhanden -> nicht anlegen (legacy Fälle ignorieren)

    # --- user (soft delete) ---
    if 'user' in tables:
        cols = {c['name'] for c in insp.get_columns('user')}
        if 'deleted_at' not in cols:
            op.add_column('user', sa.Column('deleted_at', sa.DateTime(), nullable=True))
        # Index
        idxs = {ix['name'] for ix in insp.get_indexes('user')}
        if 'ix_user_deleted_at' not in idxs and 'deleted_at' in ({c['name'] for c in insp.get_columns('user')}):
            op.create_index('ix_user_deleted_at', 'user', ['deleted_at'])

    # Keine Down-Operation (konvergenz-sicher)

def downgrade():  # pragma: no cover
    # Absichtlich leer gelassen – konvergierende Migration.
    pass
