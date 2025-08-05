"""add sent_email model

Revision ID: b7fee1a97eeb
Revises: 1c0c1ce4a3b0
Create Date: 2025-10-04 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7fee1a97eeb'
down_revision = '1c0c1ce4a3b0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sent_email',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('zajecia_id', sa.Integer(), nullable=False),
        sa.Column('recipient', sa.String(length=120), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['zajecia_id'], ['zajecia.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('sent_email')

