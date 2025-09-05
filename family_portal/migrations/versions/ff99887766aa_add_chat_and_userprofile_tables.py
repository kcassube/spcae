"""add chat_messages and user_profiles tables

Revision ID: ff99887766aa
Revises: ee1122334455
Create Date: 2025-09-04 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'ff99887766aa'
down_revision = 'ee1122334455'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if 'chat_messages' not in tables:
        op.create_table(
            'chat_messages',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False, index=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), index=True)
        )
        # Fallback: Für einige Backends erzeugt create_table() keine Indizes via Column(index=True)
        idx_names = {ix['name'] for ix in inspector.get_indexes('chat_messages')}
        if 'ix_chat_messages_user_id' not in idx_names:
            op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
        if 'ix_chat_messages_created_at' not in idx_names:
            op.create_index('ix_chat_messages_created_at', 'chat_messages', ['created_at'])

    if 'user_profiles' not in tables:
        op.create_table(
            'user_profiles',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), primary_key=True),
            sa.Column('bio', sa.Text()),
            sa.Column('avatar_filename', sa.String(length=255)),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'))
        )

def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if 'user_profiles' in tables:
        op.drop_table('user_profiles')
    if 'chat_messages' in tables:
        idx_names = {ix['name'] for ix in inspector.get_indexes('chat_messages')}
        if 'ix_chat_messages_created_at' in idx_names:
            op.drop_index('ix_chat_messages_created_at', 'chat_messages')
        if 'ix_chat_messages_user_id' in idx_names:
            op.drop_index('ix_chat_messages_user_id', 'chat_messages')
        op.drop_table('chat_messages')
