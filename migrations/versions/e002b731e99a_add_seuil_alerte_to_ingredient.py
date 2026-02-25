"""add seuil_alerte to ingredient

Revision ID: e002b731e99a
Revises: 72a868cd6479
Create Date: 2026-02-24 13:28:20.128131

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'e002b731e99a'
down_revision = '72a868cd6479'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name, column_name):
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in cols


def upgrade():
    # Create user table only if it doesn't exist yet
    if not _table_exists('user'):
        op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
        )

    # Alter ingredient table
    needs_add = not _column_exists('ingredient', 'seuil_alerte')
    needs_drop = _column_exists('ingredient', 'categorie_id')

    if needs_add or needs_drop:
        with op.batch_alter_table('ingredient', schema=None, reflect_kwargs={'resolve_fks': False}) as batch_op:
            if needs_add:
                batch_op.add_column(sa.Column('seuil_alerte', sa.Float(), nullable=True))
            if needs_drop:
                batch_op.drop_column('categorie_id')

    # Drop legacy tables if they still exist
    for tbl in ('categorie', 'bar_pointage', 'transfert', 'pointage_bar'):
        if _table_exists(tbl):
            op.drop_table(tbl)


def downgrade():
    with op.batch_alter_table('ingredient', schema=None) as batch_op:
        batch_op.add_column(sa.Column('categorie_id', sa.INTEGER(), nullable=True))
        batch_op.drop_column('seuil_alerte')

    op.drop_table('user')
