"""add push subscriptions

Revision ID: ab45cd67ef01
Revises: bb1122334455
Create Date: 2025-09-04 14:50:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ab45cd67ef01'
down_revision = 'bb1122334455'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'push_subscriptions' not in tables:
        op.create_table(
            'push_subscriptions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('endpoint', sa.Text(), nullable=False, unique=True),
            sa.Column('p256dh', sa.String(length=255), nullable=False),
            sa.Column('auth', sa.String(length=255), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
        )
    # Index nur anlegen falls nicht vorhanden
    if 'push_subscriptions' in tables:
        existing_indexes = {ix['name'] for ix in inspector.get_indexes('push_subscriptions')}
        if 'ix_push_subscriptions_user_id' not in existing_indexes:
            op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'])

def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'push_subscriptions' in tables:
        existing_indexes = {ix['name'] for ix in inspector.get_indexes('push_subscriptions')}
        if 'ix_push_subscriptions_user_id' in existing_indexes:
            op.drop_index('ix_push_subscriptions_user_id', table_name='push_subscriptions')
        op.drop_table('push_subscriptions')
