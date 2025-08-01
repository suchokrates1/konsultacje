"""add settings table

Revision ID: 4c2ac189cc2d
Revises: f134c9089658
Create Date: 2025-08-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4c2ac189cc2d'
down_revision = 'f134c9089658'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mail_server', sa.String(length=255), nullable=True),
        sa.Column('mail_port', sa.Integer(), nullable=True),
        sa.Column('mail_username', sa.String(length=255), nullable=True),
        sa.Column('mail_password', sa.String(length=255), nullable=True),
        sa.Column('timezone', sa.String(length=64), nullable=True),
    )


def downgrade():
    op.drop_table('settings')

