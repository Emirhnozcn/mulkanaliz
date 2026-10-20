
"""Add sale/rent classification to listings.

Revision ID: 0004_listing_transaction_type
Revises: 0003_usernames
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_listing_transaction_type"
down_revision: Union[str, None] = "0003_usernames"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    columns = {
        column["name"]
        for column in inspector.get_columns("listings")
    }

    # Add the column only if it does not already exist.
    if "transaction_type" not in columns:
        op.add_column(
            "listings",
            sa.Column(
                "transaction_type",
                sa.String(length=10),
                nullable=False,
                server_default="sale",
            ),
        )

    # Add the CHECK constraint if it does not already exist.
    inspector = sa.inspect(conn)
    check_constraints = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("listings")
    }

    if "listing_transaction_type_valid" not in check_constraints:
        with op.batch_alter_table("listings") as batch_op:
            batch_op.create_check_constraint(
                "listing_transaction_type_valid",
                "transaction_type IN ('sale', 'rent')",
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    check_constraints = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("listings")
    }

    columns = {
        column["name"]
        for column in inspector.get_columns("listings")
    }

    if (
        "listing_transaction_type_valid" in check_constraints
        and "transaction_type" in columns
    ):
        with op.batch_alter_table("listings") as batch_op:
            batch_op.drop_constraint(
                "listing_transaction_type_valid",
                type_="check",
            )

    # Refresh the schema after dropping the constraint.
    inspector = sa.inspect(conn)
    columns = {
        column["name"]
        for column in inspector.get_columns("listings")
    }

    if "transaction_type" in columns:
        op.drop_column("listings", "transaction_type")
