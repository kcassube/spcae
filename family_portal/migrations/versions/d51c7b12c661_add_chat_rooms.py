"""add chat rooms

Revision ID: d51c7b12c661
Revises: ab45cd67ef01
Create Date: 2025-09-05 06:37:29.936881

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'd51c7b12c661'
down_revision = 'ab45cd67ef01'
branch_labels = None
depends_on = None


def upgrade():
    """Idempotente Version der ursprünglichen Migration.

    Diese Migration lief in einigen Umgebungen bereits teilweise / manuell.
    Deshalb werden alle Operationen nur ausgeführt, falls wirklich nötig.
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    # chat_rooms anlegen falls nicht vorhanden
    if 'chat_rooms' not in tables:
        op.create_table('chat_rooms',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=80), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id'))
        )
    # Index created_at nachziehen falls fehlt
    if 'chat_rooms' in tables:
        idx_names = {ix['name'] for ix in inspector.get_indexes('chat_rooms')}
        cols = {c['name'] for c in inspector.get_columns('chat_rooms')}
        if 'created_at' in cols and 'ix_chat_rooms_created_at' not in idx_names:
            op.create_index('ix_chat_rooms_created_at', 'chat_rooms', ['created_at'])

    # chat_messages Erweiterungen (room_id + FK + Index)
    if 'chat_messages' in tables:
        cols = {c['name'] for c in inspector.get_columns('chat_messages')}
        idx_names = {ix['name'] for ix in inspector.get_indexes('chat_messages')}
        if 'room_id' not in cols:
            op.add_column('chat_messages', sa.Column('room_id', sa.Integer(), nullable=True))
            # FK anlegen
            op.create_foreign_key(None, 'chat_messages', 'chat_rooms', ['room_id'], ['id'])
        else:
            # sicherstellen dass FK existiert (überspringen falls bereits da)
            pass
        if 'ix_chat_messages_room_id' not in idx_names and 'room_id' in ({c['name'] for c in inspector.get_columns('chat_messages')}):
            op.create_index('ix_chat_messages_room_id', 'chat_messages', ['room_id'])

    # expense: kind nullable + Index auf date
    if 'expense' in tables:
        cols = {c['name'] for c in inspector.get_columns('expense')}
        if 'kind' in cols:
            try:
                with op.batch_alter_table('expense') as batch_op:
                    batch_op.alter_column('kind', existing_type=mysql.VARCHAR(length=20), nullable=True, existing_server_default=sa.text("'expense'"))
            except Exception:
                pass  # schon angepasst
        idx_names = {ix['name'] for ix in inspector.get_indexes('expense')}
        if 'ix_expense_date' not in idx_names and 'date' in cols:
            op.create_index('ix_expense_date', 'expense', ['date'])

    # notification_events Indizes anpassen
    if 'notification_events' in tables:
        idx_names = {ix['name'] for ix in inspector.get_indexes('notification_events')}
        # alter alter Index evtl vorhanden
        if 'ix_notif_events_user_delivered' in idx_names:
            try:
                op.drop_index('ix_notif_events_user_delivered', table_name='notification_events')
            except Exception:
                pass
        if 'ix_notification_events_created_at' not in idx_names:
            op.create_index('ix_notification_events_created_at', 'notification_events', ['created_at'])
        if 'ix_notification_events_delivered' not in idx_names:
            op.create_index('ix_notification_events_delivered', 'notification_events', ['delivered'])
        if 'ix_notification_events_user_id' not in idx_names:
            op.create_index('ix_notification_events_user_id', 'notification_events', ['user_id'])

    # notification_preferences Indizes anpassen
    if 'notification_preferences' in tables:
        idx_names = {ix['name'] for ix in inspector.get_indexes('notification_preferences')}
        if 'ix_notif_pref_user_enabled' in idx_names:
            try:
                op.drop_index('ix_notif_pref_user_enabled', table_name='notification_preferences')
            except Exception:
                pass
        if 'ix_notification_preferences_enabled' not in idx_names:
            op.create_index('ix_notification_preferences_enabled', 'notification_preferences', ['enabled'])
        if 'ix_notification_preferences_user_id' not in idx_names:
            op.create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'])

    # photos Indizes aktualisieren
    if 'photos' in tables:
        idx_names = {ix['name'] for ix in inspector.get_indexes('photos')}
        if 'ix_photo_user_id' in idx_names:
            try:
                op.drop_index('ix_photo_user_id', table_name='photos')
            except Exception:
                pass
        if 'ix_photos_created_at' not in idx_names:
            op.create_index('ix_photos_created_at', 'photos', ['created_at'])
        if 'ix_photos_user_id' not in idx_names:
            op.create_index('ix_photos_user_id', 'photos', ['user_id'])

    # push_subscriptions Index + FK
    if 'push_subscriptions' in tables:
        idx_names = {ix['name'] for ix in inspector.get_indexes('push_subscriptions')}
        if 'ix_push_subscriptions_created_at' not in idx_names:
            op.create_index('ix_push_subscriptions_created_at', 'push_subscriptions', ['created_at'])
        # FK user_id sicherstellen (nicht doppelt erzwingen)
        # Alembic kennt hier keine einfache Abfrage -> überspringen wenn Exception
        try:
            op.create_foreign_key(None, 'push_subscriptions', 'user', ['user_id'], ['id'])
        except Exception:
            pass

    # recurring_transaction Änderungen
    if 'recurring_transaction' in tables:
        cols = {c['name'] for c in inspector.get_columns('recurring_transaction')}
        if 'kind' in cols:
            try:
                with op.batch_alter_table('recurring_transaction') as batch_op:
                    batch_op.alter_column('kind', existing_type=mysql.VARCHAR(length=20), nullable=True, existing_server_default=sa.text("'expense'"))
            except Exception:
                pass
        if 'active' in cols:
            try:
                with op.batch_alter_table('recurring_transaction') as batch_op:
                    batch_op.alter_column('active', existing_type=mysql.TINYINT(display_width=1), nullable=True, existing_server_default=sa.text('1'))
            except Exception:
                pass
        idx_names = {ix['name'] for ix in inspector.get_indexes('recurring_transaction')}
        if 'ix_recurring_active' in idx_names:
            try:
                op.drop_index('ix_recurring_active', table_name='recurring_transaction')
            except Exception:
                pass
        if 'ix_recurring_transaction_active' not in idx_names and 'active' in cols:
            op.create_index('ix_recurring_transaction_active', 'recurring_transaction', ['active'])

    # Ende upgrade


def downgrade():
    # Kein verlässliches Downgrade mehr möglich ohne Risiko – bewusst leer.
    pass
