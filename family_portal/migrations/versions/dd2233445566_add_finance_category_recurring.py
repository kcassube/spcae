"""add category and recurring models

Revision ID: dd2233445566
Revises: ccddeeff0011
Create Date: 2025-09-04 00:25:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'dd2233445566'
down_revision = 'ccddeeff0011'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    # CATEGORY
    if 'category' not in tables:
        op.create_table('category',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('color', sa.String(length=20)),
            sa.Column('monthly_budget', sa.Float()),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id')),
            sa.Column('created_at', sa.DateTime())
        )
        op.create_index('ix_category_name', 'category', ['name'])
    else:
        # Index sicherstellen
        idx_names = {ix['name'] for ix in inspector.get_indexes('category')}
        if 'ix_category_name' not in idx_names:
            op.create_index('ix_category_name', 'category', ['name'])

    # EXPENSE category_id
    expense_cols = [c['name'] for c in inspector.get_columns('expense')]
    if 'category_id' not in expense_cols:
        with op.batch_alter_table('expense') as batch_op:
            batch_op.add_column(sa.Column('category_id', sa.Integer(), sa.ForeignKey('category.id')))

    # RECURRING TRANSACTION
    if 'recurring_transaction' not in tables:
        op.create_table('recurring_transaction',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('description', sa.String(length=120), nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('kind', sa.String(length=20), nullable=False, server_default='expense'),
            sa.Column('category', sa.String(length=64), nullable=False),
            sa.Column('category_id', sa.Integer(), sa.ForeignKey('category.id')),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('frequency', sa.String(length=20), nullable=False),
            sa.Column('last_generated_date', sa.Date()),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1'))
        )
        op.create_index('ix_recurring_active', 'recurring_transaction', ['active'])
    else:
        idx_names = {ix['name'] for ix in inspector.get_indexes('recurring_transaction')}
        if 'ix_recurring_active' not in idx_names:
            op.create_index('ix_recurring_active', 'recurring_transaction', ['active'])


def downgrade():
    op.drop_index('ix_recurring_active', 'recurring_transaction')
    op.drop_table('recurring_transaction')
    with op.batch_alter_table('expense') as batch_op:
        batch_op.drop_column('category_id')
    op.drop_index('ix_category_name', 'category')
    op.drop_table('category')
