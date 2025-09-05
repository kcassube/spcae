"""Add is_admin_only flag to chat_rooms

Revision ID: f01122334455
Revises: de11fe22aa44
Create Date: 2025-09-05 13:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'f01122334455'
down_revision = 'de11fe22aa44'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'chat_rooms' in inspector.get_table_names():
        cols = {c['name'] for c in inspector.get_columns('chat_rooms')}
        if 'is_admin_only' not in cols:
            op.add_column('chat_rooms', sa.Column('is_admin_only', sa.Boolean(), server_default=sa.text('0'), nullable=False))
            # Optional Index (falls viele Räume): bereits index=True im Model -> hier manuell erstellen
            existing = {ix['name'] for ix in inspector.get_indexes('chat_rooms')}
            if 'ix_chat_rooms_is_admin_only' not in existing:
                op.create_index('ix_chat_rooms_is_admin_only', 'chat_rooms', ['is_admin_only'])
    # Backfill: Standardräume sollen nicht admin-only sein
    try:
        bind.execute(sa.text("UPDATE chat_rooms SET is_admin_only=0 WHERE is_admin_only IS NULL"))
    except Exception:
        pass

def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'chat_rooms' in inspector.get_table_names():
        existing = {ix['name'] for ix in inspector.get_indexes('chat_rooms')}
        if 'ix_chat_rooms_is_admin_only' in existing:
            op.drop_index('ix_chat_rooms_is_admin_only', 'chat_rooms')
        cols = {c['name'] for c in inspector.get_columns('chat_rooms')}
        if 'is_admin_only' in cols:
            op.drop_column('chat_rooms', 'is_admin_only')
