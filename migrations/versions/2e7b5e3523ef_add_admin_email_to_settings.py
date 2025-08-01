"""add admin_email field to settings

Revision ID: 2e7b5e3523ef
Revises: a43a4fb8bf03
Create Date: 2025-08-01 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2e7b5e3523ef'
down_revision = 'a43a4fb8bf03'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('settings', sa.Column('admin_email', sa.String(length=120), nullable=True))


def downgrade():
    op.drop_column('settings', 'admin_email')
