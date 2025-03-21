"""add_organizations_table

Revision ID: f9ff4b9d6477
Revises: 8eb08eb72113
Create Date: 2023-09-06 20:46:09.233497

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f9ff4b9d6477"
down_revision = "8eb08eb72113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "organization",
        sa.Column("uuid", postgresql.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("uuid", name=op.f("organization_pkey")),
    )
    op.add_column(
        "auth_user", sa.Column("organization_uuid", postgresql.UUID(), nullable=True)
    )
    op.create_foreign_key(
        op.f("auth_user_organization_uuid_fkey"),
        "auth_user",
        "organization",
        ["organization_uuid"],
        ["uuid"],
        ondelete="NO ACTION",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("auth_user_organization_uuid_fkey"), "auth_user", type_="foreignkey"
    )
    op.drop_column("auth_user", "organization_uuid")
    op.drop_table("organization")
    # ### end Alembic commands ###
