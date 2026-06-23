"""add projekt model and project scoping

Revision ID: d4e8f1a2b3c4
Revises: c35bb5940733
Create Date: 2026-06-24 00:00:00.000000

"""
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = 'd4e8f1a2b3c4'
down_revision = 'c35bb5940733'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'projekt',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nazwa', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('utworzono', sa.DateTime(), nullable=False),
        sa.Column('zarchiwizowano', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nazwa'),
    )

    op.add_column('beneficjent', sa.Column('project_id', sa.Integer(), nullable=True))
    op.add_column('zajecia', sa.Column('project_id', sa.Integer(), nullable=True))

    now = datetime.now(UTC).replace(tzinfo=None)
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO projekt (id, nazwa, status, utworzono, zarchiwizowano) "
            "VALUES (1, 'ATNIS V', 'archiwum', :now, :now)"
        ),
        {'now': now},
    )
    conn.execute(
        sa.text(
            "INSERT INTO projekt (id, nazwa, status, utworzono, zarchiwizowano) "
            "VALUES (2, 'ATNIS VI', 'aktywny', :now, NULL)"
        ),
        {'now': now},
    )

    conn.execute(sa.text("UPDATE beneficjent SET project_id = 1"))
    conn.execute(sa.text("UPDATE zajecia SET project_id = 1"))

    with op.batch_alter_table('beneficjent') as batch_op:
        batch_op.alter_column('project_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_beneficjent_project_id', 'projekt', ['project_id'], ['id']
        )

    with op.batch_alter_table('zajecia') as batch_op:
        batch_op.alter_column('project_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_zajecia_project_id', 'projekt', ['project_id'], ['id']
        )


def downgrade():
    with op.batch_alter_table('zajecia') as batch_op:
        batch_op.drop_constraint('fk_zajecia_project_id', type_='foreignkey')
        batch_op.drop_column('project_id')

    with op.batch_alter_table('beneficjent') as batch_op:
        batch_op.drop_constraint('fk_beneficjent_project_id', type_='foreignkey')
        batch_op.drop_column('project_id')

    op.drop_table('projekt')
