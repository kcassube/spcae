"""add accounts and account_transactions

Revision ID: aa55bb66cc77
Revises: fe2233445566_converge_chat_user_soft_delete
Create Date: 2025-09-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'aa55bb66cc77'
down_revision = 'fe2233445566_converge_chat_user_soft_delete'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=80), nullable=False, unique=True),
        sa.Column('balance', sa.Float(), nullable=False, server_default='0'),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id')),
        sa.Column('created_at', sa.DateTime(), index=True)
    )
    op.create_table('account_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('from_account_id', sa.Integer(), sa.ForeignKey('accounts.id')),
        sa.Column('to_account_id', sa.Integer(), sa.ForeignKey('accounts.id')),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.String(length=200)),
        sa.Column('created_at', sa.DateTime(), index=True),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False)
    )


def downgrade():
    op.drop_table('account_transactions')
    op.drop_table('accounts')
