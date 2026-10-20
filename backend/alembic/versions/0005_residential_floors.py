
"""Add residential floor fields for imported listings.

Revision ID: 0005_residential_floors
Revises: 0004_listing_transaction_type
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_residential_floors"
down_revision: Union[str, None] = "0004_listing_transaction_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("residential_details")
    }

    if "floor_number" not in existing_columns:
        op.add_column(
            "residential_details",
            sa.Column("floor_number", sa.SmallInteger(), nullable=True),
        )

    if "total_floors" not in existing_columns:
        op.add_column(
            "residential_details",
            sa.Column("total_floors", sa.SmallInteger(), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("residential_details")
    }

    if "total_floors" in existing_columns:
        op.drop_column("residential_details", "total_floors")

    if "floor_number" in existing_columns:
        op.drop_column("residential_details", "floor_number")
