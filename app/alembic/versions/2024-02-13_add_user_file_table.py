"""add_user_file_table

Revision ID: f7246f938610
Revises: 42180b403ff1
Create Date: 2024-02-13 02:42:13.567102

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.db_types import AwareDateTime

# revision identifiers, used by Alembic.
revision = "f7246f938610"
down_revision = "42180b403ff1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user_file",
        sa.Column("uuid", postgresql.UUID(), nullable=False),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("optimized_content", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_value", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("user", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            AwareDateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            AwareDateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user"], ["auth_user.id"], ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("user_file")
    # ### end Alembic commands ###
