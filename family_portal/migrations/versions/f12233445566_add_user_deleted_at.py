"""Add deleted_at to user for soft delete

Revision ID: f12233445566
Revises: f01122334455
Create Date: 2025-09-05 13:50:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'f12233445566'
down_revision = 'f01122334455'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    if 'user' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('user')}
        if 'deleted_at' not in cols:
            op.add_column('user', sa.Column('deleted_at', sa.DateTime(), nullable=True))
            # index
            existing = {ix['name'] for ix in insp.get_indexes('user')}
            if 'ix_user_deleted_at' not in existing:
                op.create_index('ix_user_deleted_at', 'user', ['deleted_at'])

def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    if 'user' in insp.get_table_names():
        existing = {ix['name'] for ix in insp.get_indexes('user')}
        if 'ix_user_deleted_at' in existing:
            op.drop_index('ix_user_deleted_at', 'user')
        cols = {c['name'] for c in insp.get_columns('user')}
        if 'deleted_at' in cols:
            op.drop_column('user', 'deleted_at')
