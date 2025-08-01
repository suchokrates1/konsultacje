"""add tls/ssl fields to settings

Revision ID: 03c521f58674
Revises: 4c2ac189cc2d
Create Date: 2025-08-01 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '03c521f58674'
down_revision = '4c2ac189cc2d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('settings', sa.Column('mail_use_tls', sa.Boolean(), nullable=True))
    op.add_column('settings', sa.Column('mail_use_ssl', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('settings', 'mail_use_ssl')
    op.drop_column('settings', 'mail_use_tls')
