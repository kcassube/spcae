"""Add account_id to expense & recurring_transaction

Revision ID: an4455667788
Revises: mg4455667788
Create Date: 2025-09-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'an4455667788'
down_revision = 'mg4455667788'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if 'expense' in tables:
        cols = {c['name'] for c in insp.get_columns('expense')}
        if 'account_id' not in cols:
            op.add_column('expense', sa.Column('account_id', sa.Integer(), nullable=True))
            op.create_index('ix_expense_account_id', 'expense', ['account_id'])
            try:
                op.create_foreign_key(None, 'expense', 'accounts', ['account_id'], ['id'])
            except Exception:
                pass
    if 'recurring_transaction' in tables:
        cols = {c['name'] for c in insp.get_columns('recurring_transaction')}
        if 'account_id' not in cols:
            op.add_column('recurring_transaction', sa.Column('account_id', sa.Integer(), nullable=True))
            op.create_index('ix_recurring_transaction_account_id', 'recurring_transaction', ['account_id'])
            try:
                op.create_foreign_key(None, 'recurring_transaction', 'accounts', ['account_id'], ['id'])
            except Exception:
                pass

def downgrade():  # pragma: no cover
    bind = op.get_bind()
    insp = inspect(bind)
    if 'expense' in insp.get_table_names():
        try:
            op.drop_index('ix_expense_account_id', table_name='expense')
        except Exception:
            pass
        try:
            op.drop_column('expense', 'account_id')
        except Exception:
            pass
    if 'recurring_transaction' in insp.get_table_names():
        try:
            op.drop_index('ix_recurring_transaction_account_id', table_name='recurring_transaction')
        except Exception:
            pass
        try:
            op.drop_column('recurring_transaction', 'account_id')
        except Exception:
            pass
