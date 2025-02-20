"""add_message_vector

Revision ID: 4c52b7bd9194
Revises: 6c8b28a13c55
Create Date: 2024-09-26 15:08:49.740436

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils.types import TSVectorType

# revision identifiers, used by Alembic.
revision = "4c52b7bd9194"
down_revision = "6c8b28a13c55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "message",
        sa.Column(
            "search_vector",
            TSVectorType(),
            nullable=True,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("message", "search_vector")
    # ### end Alembic commands ###
