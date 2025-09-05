"""merge heads

Revision ID: ccddeeff0011
Revises: ab12c34d56ef, 499b6d42f2d6
Create Date: 2025-09-04 00:05:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'ccddeeff0011'
down_revision = ('ab12c34d56ef', '499b6d42f2d6')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
