"""store role values

Revision ID: c35bb5940733
Revises: 8bd82fd7018c
Create Date: 2025-08-08 21:48:55.806023

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c35bb5940733'
down_revision = '8bd82fd7018c'
branch_labels = None
depends_on = None


old_roles = sa.Enum("ADMIN", "INSTRUCTOR", name="roles")
new_roles = sa.Enum("admin", "instructor", "superadmin", name="roles")


def upgrade():
    """Switch user.role to store enum values instead of names."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE roles RENAME TO roles_old")
        new_roles.create(bind)
        op.execute(
            'ALTER TABLE "user" ALTER COLUMN role TYPE roles USING LOWER(role)::text::roles'
        )
        op.execute("DROP TYPE roles_old")
    else:
        op.execute("UPDATE user SET role = LOWER(role)")
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.alter_column(
                "role", existing_type=old_roles, type_=new_roles, existing_nullable=True
            )


def downgrade():
    """Revert user.role to store enum names."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE roles RENAME TO roles_old")
        old_roles.create(bind)
        op.execute(
            'ALTER TABLE "user" ALTER COLUMN role TYPE roles USING UPPER(role)::text::roles'
        )
        op.execute("DROP TYPE roles_old")
    else:
        op.execute("UPDATE user SET role = UPPER(role)")
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.alter_column(
                "role", existing_type=new_roles, type_=old_roles, existing_nullable=True
            )
