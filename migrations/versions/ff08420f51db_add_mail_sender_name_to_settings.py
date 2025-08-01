"""add mail_sender_name field to settings

Revision ID: ff08420f51db
Revises: 2e7b5e3523ef
Create Date: 2025-08-01 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ff08420f51db'
down_revision = '2e7b5e3523ef'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('settings', sa.Column('mail_sender_name', sa.String(length=120), nullable=True))


def downgrade():
    op.drop_column('settings', 'mail_sender_name')
