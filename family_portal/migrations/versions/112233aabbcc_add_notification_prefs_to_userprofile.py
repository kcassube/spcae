"""add notification_prefs to user_profiles

Revision ID: 112233aabbcc
Revises: aa1122334455
Create Date: 2025-09-04 13:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '112233aabbcc'
down_revision = 'aa1122334455'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('user_profiles')]
    if 'notification_prefs' not in cols:
        op.add_column('user_profiles', sa.Column('notification_prefs', sa.String(length=500)))


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('user_profiles')]
    if 'notification_prefs' in cols:
        op.drop_column('user_profiles', 'notification_prefs')
