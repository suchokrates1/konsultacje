"""Change user.role column to Enum."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8bd82fd7018c'
down_revision = 'f9b94a4c8dc3'
branch_labels = None
depends_on = None


roles_enum = sa.Enum('ADMIN', 'INSTRUCTOR', name='roles')


def upgrade():
    roles_enum.create(op.get_bind(), checkfirst=True)
    op.execute("UPDATE user SET role = UPPER(role)")
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'role',
            existing_type=sa.String(length=20),
            type_=roles_enum,
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'role',
            existing_type=roles_enum,
            type_=sa.String(length=20),
            existing_nullable=True,
        )
    roles_enum.drop(op.get_bind(), checkfirst=True)
