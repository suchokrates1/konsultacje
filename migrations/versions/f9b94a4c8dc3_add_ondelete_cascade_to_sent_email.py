"""add ondelete cascade to sent_email.zajecia_id

Revision ID: f9b94a4c8dc3
Revises: 11045d5514ab
Create Date: 2025-10-08 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f9b94a4c8dc3'
down_revision = '11045d5514ab'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sent_email', recreate='always') as batch_op:
        batch_op.create_foreign_key(
            'sent_email_zajecia_id_fkey',
            'zajecia',
            ['zajecia_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade():
    with op.batch_alter_table('sent_email', recreate='always') as batch_op:
        batch_op.create_foreign_key(
            'sent_email_zajecia_id_fkey',
            'zajecia',
            ['zajecia_id'],
            ['id'],
        )
