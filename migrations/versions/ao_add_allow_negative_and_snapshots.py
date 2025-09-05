"""Add allow_negative to accounts and snapshot table

Revision ID: ao5566778899
Revises: an4455667788
Create Date: 2025-09-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'ao5566778899'
down_revision = 'an4455667788'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if 'accounts' in tables:
        cols = {c['name'] for c in insp.get_columns('accounts')}
        if 'allow_negative' not in cols:
            op.add_column('accounts', sa.Column('allow_negative', sa.Boolean(), nullable=False, server_default=sa.text('0')))
            op.create_index('ix_accounts_allow_negative', 'accounts', ['allow_negative'])
    if 'account_balance_snapshot' not in tables:
        op.create_table('account_balance_snapshot',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False, index=True),
            sa.Column('day', sa.Date(), nullable=False, index=True),
            sa.Column('balance', sa.Float(), nullable=False),
            sa.Column('created_at', sa.DateTime()),
            sa.UniqueConstraint('account_id','day', name='uq_snapshot_account_day')
        )
        op.create_index('ix_snapshot_account_day', 'account_balance_snapshot', ['account_id','day'])

def downgrade():  # pragma: no cover
    bind = op.get_bind()
    insp = inspect(bind)
    if 'account_balance_snapshot' in insp.get_table_names():
        try:
            op.drop_index('ix_snapshot_account_day', table_name='account_balance_snapshot')
        except Exception:
            pass
        op.drop_table('account_balance_snapshot')
    if 'accounts' in insp.get_table_names():
        try:
            op.drop_index('ix_accounts_allow_negative', table_name='accounts')
        except Exception:
            pass
        try:
            op.drop_column('accounts','allow_negative')
        except Exception:
            pass
