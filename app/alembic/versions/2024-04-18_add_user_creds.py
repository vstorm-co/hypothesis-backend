"""add_user_creds

Revision ID: 3500f4145a8d
Revises: 2b2c419c394d
Create Date: 2024-04-18 12:21:09.572471

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3500f4145a8d"
down_revision = "2b2c419c394d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("auth_user", sa.Column("credentials", sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("auth_user", "credentials")
    # ### end Alembic commands ###
