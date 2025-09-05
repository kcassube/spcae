"""rename photo table to photos and adjust columns

Revision ID: aa1122334455
Revises: ff99887766aa
Create Date: 2025-09-04 13:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = 'aa1122334455'
down_revision = 'ff99887766aa'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    # Case 1: legacy 'photo' table exists
    if 'photo' in tables:
        cols = {c['name'] for c in insp.get_columns('photo')}
        # Rename upload_date -> created_at if needed
        if 'upload_date' in cols and 'created_at' not in cols:
            op.alter_column('photo', 'upload_date', new_column_name='created_at', existing_type=sa.DateTime())
        # Drop description column (no longer used by model)
        cols = {c['name'] for c in insp.get_columns('photo')}
        if 'description' in cols:
            with op.batch_alter_table('photo') as batch:
                batch.drop_column('description')
        # Add user_id index (if missing)
        idx_names = {ix['name'] for ix in insp.get_indexes('photo')}
        if 'ix_photo_user_id' not in idx_names and 'user_id' in cols:
            op.create_index('ix_photo_user_id', 'photo', ['user_id'])
        if 'ix_photo_created_at' not in idx_names and 'created_at' in cols:
            op.create_index('ix_photo_created_at', 'photo', ['created_at'])
        # Ensure filename uniqueness (adds unique index if not present)
        # MySQL workaround: check if duplicate filenames exist first
        if bind.dialect.name == 'mysql':
            dup_check = bind.execute(text("SELECT filename, COUNT(*) c FROM photo GROUP BY filename HAVING c>1 LIMIT 1")).fetchone()
            if not dup_check:
                # create unique index if not already
                if 'ux_photo_filename' not in idx_names:
                    op.create_index('ux_photo_filename', 'photo', ['filename'], unique=True)
        else:
            if 'ux_photo_filename' not in idx_names:
                op.create_index('ux_photo_filename', 'photo', ['filename'], unique=True)
        # Finally rename table to 'photos'
        op.rename_table('photo', 'photos')
        tables.add('photos')

    # Case 2: neither legacy nor new table exists -> create fresh 'photos'
    tables = set(insp.get_table_names())
    if 'photo' not in tables and 'photos' not in tables:
        op.create_table('photos',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('filename', sa.String(length=255), nullable=False),
            sa.Column('title', sa.String(length=120)),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'))
        )
        op.create_index('ix_photo_user_id', 'photos', ['user_id'])
        op.create_index('ix_photo_created_at', 'photos', ['created_at'])
        op.create_index('ux_photo_filename', 'photos', ['filename'], unique=True)


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if 'photos' in tables:
        # Attempt to rename back and reverse minimal changes
        cols = {c['name'] for c in insp.get_columns('photos')}
        idx_names = {ix['name'] for ix in insp.get_indexes('photos')}
        if 'ux_photo_filename' in idx_names:
            op.drop_index('ux_photo_filename', 'photos')
        if 'ix_photo_created_at' in idx_names:
            op.drop_index('ix_photo_created_at', 'photos')
        if 'ix_photo_user_id' in idx_names:
            op.drop_index('ix_photo_user_id', 'photos')
        # Rename created_at back if upload_date absent
        if 'created_at' in cols and 'upload_date' not in cols:
            op.alter_column('photos', 'created_at', new_column_name='upload_date', existing_type=sa.DateTime())
        op.rename_table('photos', 'photo')
