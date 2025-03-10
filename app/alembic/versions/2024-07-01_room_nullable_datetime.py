"""fix_datetime_nullable_false

Revision ID: 1e6594d2a346
Revises: eb38eaef1e40
Create Date: 2024-07-01 14:14:29.381777

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.db_types import AwareDateTime

# revision identifiers, used by Alembic.
revision = "1e6594d2a346"
down_revision = "eb38eaef1e40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "auth_refresh_token",
        "expires_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "auth_refresh_token",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "auth_refresh_token",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=True,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "auth_user",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "auth_user",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=True,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "message",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "message",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=True,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=True,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization_admin",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization_user",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "room",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "room",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "template",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "template",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=AwareDateTime(timezone=True),
        existing_nullable=True,
        server_default=sa.text("now()"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "template",
        "updated_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "template",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "room",
        "updated_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        nullable=True,
    )
    op.alter_column(
        "room",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization_user",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization_admin",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization",
        "updated_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "organization",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "message",
        "updated_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "message",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "auth_user",
        "updated_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "auth_user",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "auth_refresh_token",
        "updated_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "auth_refresh_token",
        "created_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "auth_refresh_token",
        "expires_at",
        existing_type=AwareDateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=False,
    )
    # ### end Alembic commands ###
