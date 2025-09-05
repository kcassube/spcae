"""add notification preference and event tables

Revision ID: bb1122334455
Revises: 112233aabbcc
Create Date: 2025-09-04 13:50:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'bb1122334455'
down_revision = '112233aabbcc'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if 'notification_preferences' not in tables:
        op.create_table('notification_preferences',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('channel', sa.String(length=20), nullable=False),
            sa.Column('kind', sa.String(length=30), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('updated_at', sa.DateTime()),
            sa.UniqueConstraint('user_id','channel','kind', name='uq_pref_user_channel_kind')
        )
    # Index prüfen
    if 'notification_preferences' in tables:
        idxs = {ix['name'] for ix in insp.get_indexes('notification_preferences')}
        if 'ix_notif_pref_user_enabled' not in idxs and {'user_id','enabled'}.issubset({c['name'] for c in insp.get_columns('notification_preferences')}):
            op.create_index('ix_notif_pref_user_enabled', 'notification_preferences', ['user_id','enabled'])

    if 'notification_events' not in tables:
        op.create_table('notification_events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('kind', sa.String(length=30), nullable=False),
            sa.Column('channel', sa.String(length=20), nullable=False),
            sa.Column('payload', sa.Text()),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('delivered', sa.Boolean(), server_default=sa.text('0')),
            sa.Column('delivered_at', sa.DateTime())
        )
    if 'notification_events' in tables:
        idxs = {ix['name'] for ix in insp.get_indexes('notification_events')}
        if 'ix_notif_events_user_delivered' not in idxs and {'user_id','delivered'}.issubset({c['name'] for c in insp.get_columns('notification_events')}):
            op.create_index('ix_notif_events_user_delivered', 'notification_events', ['user_id','delivered'])


def downgrade():
    op.drop_index('ix_notif_events_user_delivered', 'notification_events')
    op.drop_table('notification_events')
    op.drop_index('ix_notif_pref_user_enabled', 'notification_preferences')
    op.drop_table('notification_preferences')
