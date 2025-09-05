"""Merge heads ab45cd67ef01 & cc11dd22ee33 and converge schema

Revision ID: fm2233445566
Revises: ab45cd67ef01, cc11dd22ee33
Create Date: 2025-09-05 14:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = 'fm2233445566'
down_revision = ('ab45cd67ef01','cc11dd22ee33')
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    # Ensure notification tables (if prior migration skipped)
    if 'notification_preferences' not in tables:
        op.create_table('notification_preferences',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('channel', sa.String(20), nullable=False),
            sa.Column('kind', sa.String(30), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('updated_at', sa.DateTime()),
            sa.UniqueConstraint('user_id','channel','kind', name='uq_pref_user_channel_kind')
        )
    if 'notification_preferences' in tables:
        idxs = {ix['name'] for ix in insp.get_indexes('notification_preferences')}
        if 'ix_notif_pref_user_enabled' not in idxs:
            op.create_index('ix_notif_pref_user_enabled', 'notification_preferences', ['user_id','enabled'])

    if 'notification_events' not in tables:
        op.create_table('notification_events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('kind', sa.String(30), nullable=False),
            sa.Column('channel', sa.String(20), nullable=False),
            sa.Column('payload', sa.Text()),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('delivered', sa.Boolean(), server_default=sa.text('0')),
            sa.Column('delivered_at', sa.DateTime())
        )
    if 'notification_events' in tables:
        idxs = {ix['name'] for ix in insp.get_indexes('notification_events')}
        if 'ix_notif_events_user_delivered' not in idxs:
            op.create_index('ix_notif_events_user_delivered', 'notification_events', ['user_id','delivered'])

    # Chat Rooms adjustments
    if 'chat_rooms' in tables:
        cols = {c['name'] for c in insp.get_columns('chat_rooms')}
        idxs = {ix['name'] for ix in insp.get_indexes('chat_rooms')}
        if 'last_message_at' not in cols:
            op.add_column('chat_rooms', sa.Column('last_message_at', sa.DateTime(), nullable=True))
        if 'is_admin_only' not in cols:
            op.add_column('chat_rooms', sa.Column('is_admin_only', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        idxs = {ix['name'] for ix in insp.get_indexes('chat_rooms')}
        if 'ix_chat_rooms_last_message_at' not in idxs:
            op.create_index('ix_chat_rooms_last_message_at', 'chat_rooms', ['last_message_at'])
        if 'ix_chat_rooms_is_admin_only' not in idxs:
            op.create_index('ix_chat_rooms_is_admin_only', 'chat_rooms', ['is_admin_only'])
        if 'ix_chat_rooms_created_at' not in idxs and 'created_at' in cols:
            op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])
    else:
        op.create_table(
            'chat_rooms',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(80), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id')),
            sa.Column('last_message_at', sa.DateTime()),
            sa.Column('is_admin_only', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )
        op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])
        op.create_index('ix_chat_rooms_last_message_at', 'chat_rooms', ['last_message_at'])
        op.create_index('ix_chat_rooms_is_admin_only', 'chat_rooms', ['is_admin_only'])

    # Chat Messages adjustments
    if 'chat_messages' in tables:
        cols = {c['name'] for c in insp.get_columns('chat_messages')}
        idxs = {ix['name'] for ix in insp.get_indexes('chat_messages')}
        if 'room_id' not in cols:
            op.add_column('chat_messages', sa.Column('room_id', sa.Integer(), sa.ForeignKey('chat_rooms.id'), nullable=True))
        if 'archived_at' not in cols:
            op.add_column('chat_messages', sa.Column('archived_at', sa.DateTime(), nullable=True))
        idxs = {ix['name'] for ix in insp.get_indexes('chat_messages')}
        if 'ix_chat_messages_room_id_id' not in idxs and {'room_id','id'}.issubset(cols):
            op.create_index('ix_chat_messages_room_id_id', 'chat_messages', ['room_id','id'])
        if 'ix_chat_messages_archived_at' not in idxs and 'archived_at' in cols:
            op.create_index('ix_chat_messages_archived_at', 'chat_messages', ['archived_at'])
        try:
            res = bind.execute(text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()
            if not res:
                bind.execute(text("INSERT INTO chat_rooms (name) VALUES (:n)"), {"n": 'Allgemein'})
                res = bind.execute(text("SELECT id FROM chat_rooms WHERE name=:n"), {"n": 'Allgemein'}).fetchone()
            default_room_id = res[0]
            if 'room_id' in cols:
                bind.execute(text("UPDATE chat_messages SET room_id=:rid WHERE room_id IS NULL"), {"rid": default_room_id})
        except Exception:
            pass

    # User soft delete
    if 'user' in tables:
        cols = {c['name'] for c in insp.get_columns('user')}
        if 'deleted_at' not in cols:
            op.add_column('user', sa.Column('deleted_at', sa.DateTime(), nullable=True))
        idxs = {ix['name'] for ix in insp.get_indexes('user')}
        if 'ix_user_deleted_at' not in idxs and 'deleted_at' in {c['name'] for c in insp.get_columns('user')}:
            op.create_index('ix_user_deleted_at', 'user', ['deleted_at'])


def downgrade():
    # Merge Migration: kein Downgrade (bewusst leer)
    pass
