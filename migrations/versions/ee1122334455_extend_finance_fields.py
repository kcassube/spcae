"""extend finance fields (category_type, payment_method, notes)"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'ee1122334455'
down_revision = 'dd2233445566'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # Category.category_type
    cat_cols = [c['name'] for c in insp.get_columns('category')]
    if 'category_type' not in cat_cols:
        op.add_column('category', sa.Column('category_type', sa.String(length=10), server_default='expense'))
        op.create_index('ix_category_category_type', 'category', ['category_type'])

    # Expense.payment_method / notes
    exp_cols = [c['name'] for c in insp.get_columns('expense')]
    if 'payment_method' not in exp_cols:
        op.add_column('expense', sa.Column('payment_method', sa.String(length=30)))
    if 'notes' not in exp_cols:
        op.add_column('expense', sa.Column('notes', sa.Text()))

def downgrade():
    with op.batch_alter_table('expense') as b:
        b.drop_column('notes')
        b.drop_column('payment_method')
    with op.batch_alter_table('category') as b:
        b.drop_index('ix_category_category_type')
        b.drop_column('category_type')