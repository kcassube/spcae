"""Add chat rooms, room_id, soft delete and indices

Revision ID: cc11dd22ee33
Revises: ff99887766aa
Create Date: 2025-09-05 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'cc11dd22ee33'
down_revision = 'ff99887766aa'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    # Chat rooms table
    if 'chat_rooms' not in tables:
        op.create_table(
            'chat_rooms',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=80), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')), 
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id')),
            sa.Column('last_message_at', sa.DateTime())
        )
        op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])
        op.create_index('ix_chat_rooms_last_message_at', 'chat_rooms', ['last_message_at'])

    # chat_messages augmentation
    cols = {c['name'] for c in inspector.get_columns('chat_messages')} if 'chat_messages' in tables else set()
    if 'room_id' not in cols:
        op.add_column('chat_messages', sa.Column('room_id', sa.Integer(), sa.ForeignKey('chat_rooms.id'), nullable=True))
        # default all existing messages to room 1 after ensuring default room
    if 'archived_at' not in cols:
        op.add_column('chat_messages', sa.Column('archived_at', sa.DateTime(), nullable=True))

    # Indices for performance
    existing_indexes = {ix['name'] for ix in inspector.get_indexes('chat_messages')} if 'chat_messages' in tables else set()
    if 'ix_chat_messages_room_id_id' not in existing_indexes:
        op.create_index('ix_chat_messages_room_id_id', 'chat_messages', ['room_id','id'])
    if 'ix_chat_messages_archived_at' not in existing_indexes:
        op.create_index('ix_chat_messages_archived_at', 'chat_messages', ['archived_at'])

    # Initialize default room and backfill room_id
    if 'chat_rooms' in tables:
        conn = bind
        # ensure default room exists
        default_room_id = None
        res = conn.execute(sa.text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()
        if res:
            default_room_id = res[0]
        else:
            conn.execute(sa.text("INSERT INTO chat_rooms (name) VALUES (:n)"), {"n": 'Allgemein'})
            default_room_id = conn.execute(sa.text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()[0]
        if 'room_id' not in cols:
            # newly added column is NULL now; set to default
            conn.execute(sa.text("UPDATE chat_messages SET room_id=:rid WHERE room_id IS NULL"), {"rid": default_room_id})
        # WICHTIG: Kein ALTER NOT NULL mehr (verursachte DataError 1265 bei inkonsistenten Daten)
        # Anwendung erzwingt room_id ohnehin beim Erstellen neuer Nachrichten.

def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if 'chat_messages' in tables:
        idx = {ix['name'] for ix in inspector.get_indexes('chat_messages')}
        if 'ix_chat_messages_archived_at' in idx:
            op.drop_index('ix_chat_messages_archived_at', 'chat_messages')
        if 'ix_chat_messages_room_id_id' in idx:
            op.drop_index('ix_chat_messages_room_id_id', 'chat_messages')
        cols = {c['name'] for c in inspector.get_columns('chat_messages')}
        if 'archived_at' in cols:
            op.drop_column('chat_messages', 'archived_at')
        if 'room_id' in cols:
            op.drop_column('chat_messages', 'room_id')
    if 'chat_rooms' in tables:
        op.drop_index('ix_chat_rooms_last_message_at', 'chat_rooms')
        op.drop_index('ix_chat_rooms_created_at', 'chat_rooms')
        op.drop_table('chat_rooms')
