"""add kind field to expense

Revision ID: ab12c34d56ef
Revises: 976d7265329b
Create Date: 2025-09-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ab12c34d56ef'
down_revision = '976d7265329b'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('expense') as batch_op:
        batch_op.add_column(sa.Column('kind', sa.String(length=20), nullable=True))
        batch_op.create_index('ix_expense_kind', ['kind'], unique=False)
    # Set default values
    op.execute("UPDATE expense SET kind='expense'")
    with op.batch_alter_table('expense') as batch_op:
        batch_op.alter_column('kind', existing_type=sa.String(length=20), nullable=False, server_default='expense')


def downgrade():
    with op.batch_alter_table('expense') as batch_op:
        batch_op.drop_index('ix_expense_kind')
        batch_op.drop_column('kind')
