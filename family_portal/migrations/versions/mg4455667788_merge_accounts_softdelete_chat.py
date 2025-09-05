"""Merge heads for accounts + soft delete + chat convergence

Revision ID: mg4455667788
Revises: aa55bb66cc77, f12233445566, fm2233445566
Create Date: 2025-09-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'mg4455667788'
down_revision = ('aa55bb66cc77','f12233445566','fm2233445566')
branch_labels = None
depends_on = None

def upgrade():
    # Merge only, no schema changes required (accounts already introduced, other heads converged)
    pass


def downgrade():  # pragma: no cover
    # Not attempting to un-merge branches.
    pass
