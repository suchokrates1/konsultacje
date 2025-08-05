"""add doc_sent_at column to zajecia

Revision ID: 1c0c1ce4a3b0
Revises: 65ed717d04cb
Create Date: 2025-09-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c0c1ce4a3b0'
down_revision = '65ed717d04cb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('zajecia', sa.Column('doc_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('zajecia', 'doc_sent_at')
