"""add sender_name field to settings

Revision ID: 3a98bc6e1d5f
Revises: 2e7b5e3523ef
Create Date: 2025-08-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3a98bc6e1d5f'
down_revision = '2e7b5e3523ef'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('settings', sa.Column('sender_name', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('settings', 'sender_name')
