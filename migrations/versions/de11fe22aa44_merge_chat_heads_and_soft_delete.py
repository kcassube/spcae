"""Merge chat heads and ensure soft delete columns / indices

Revision ID: de11fe22aa44
Revises: d51c7b12c661, cc11dd22ee33
Create Date: 2025-09-05 11:15:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = 'de11fe22aa44'
down_revision = ('d51c7b12c661', 'cc11dd22ee33')
branch_labels = None
depends_on = None

def upgrade():
    """Merge branches and converge schema.
    This migration is defensive/idempotent: it only adds missing columns / indexes.
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    # Ensure chat_rooms table columns exist (last_message_at)
    if 'chat_rooms' in tables:
        cols = {c['name'] for c in inspector.get_columns('chat_rooms')}
        if 'last_message_at' not in cols:
            op.add_column('chat_rooms', sa.Column('last_message_at', sa.DateTime(), nullable=True))
        idx_names = {ix['name'] for ix in inspector.get_indexes('chat_rooms')}
        if 'ix_chat_rooms_last_message_at' not in idx_names:
            op.create_index('ix_chat_rooms_last_message_at', 'chat_rooms', ['last_message_at'])
        if 'ix_chat_rooms_created_at' not in idx_names and 'created_at' in cols:
            op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])
    else:
        # If neither branch created table (unlikely), create full spec
        op.create_table(
            'chat_rooms',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(80), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id')),
            sa.Column('last_message_at', sa.DateTime())
        )
        op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])
        op.create_index('ix_chat_rooms_last_message_at', 'chat_rooms', ['last_message_at'])

    # chat_messages adjustments
    if 'chat_messages' in tables:
        cols = {c['name'] for c in inspector.get_columns('chat_messages')}
        if 'room_id' not in cols:
            op.add_column('chat_messages', sa.Column('room_id', sa.Integer(), sa.ForeignKey('chat_rooms.id'), nullable=True))
        if 'archived_at' not in cols:
            op.add_column('chat_messages', sa.Column('archived_at', sa.DateTime(), nullable=True))
        # Indexes
        idx = {ix['name'] for ix in inspector.get_indexes('chat_messages')}
        if 'ix_chat_messages_room_id_id' not in idx and 'room_id' in cols and 'id' in cols:
            op.create_index('ix_chat_messages_room_id_id', 'chat_messages', ['room_id','id'])
        if 'ix_chat_messages_archived_at' not in idx and 'archived_at' in cols:
            op.create_index('ix_chat_messages_archived_at', 'chat_messages', ['archived_at'])
        # Backfill room_id if nullable
        # (Set to default room if available)
        try:
            res = bind.execute(text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()
            if not res:
                bind.execute(text("INSERT INTO chat_rooms (name) VALUES (:n)"), {"n": 'Allgemein'})
                res = bind.execute(text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()
            default_room_id = res[0]
            if 'room_id' in cols:
                # Set NULL room_id values (keine NOT NULL Erzwingung um DataError 1265 zu vermeiden)
                bind.execute(text("UPDATE chat_messages SET room_id=:rid WHERE room_id IS NULL"), {"rid": default_room_id})
        except Exception:
            pass  # If anything fails, we keep migration non-fatal


def downgrade():
    # This merge migration does not attempt to fully reverse; keep simple.
    # (Optional: Could drop added columns, but safer to leave schema.)
    pass
