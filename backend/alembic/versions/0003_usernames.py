
"""Add unique usernames for username-based authentication.

Revision ID: 0003_usernames
Revises: 0002_token_version
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_usernames"
down_revision: Union[str, None] = "0002_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    # Add the column only if it does not already exist.
    if "username" not in columns:
        op.add_column(
            "users",
            sa.Column("username", sa.String(length=40), nullable=True),
        )

    # Generate usernames for existing accounts.
    # CAST works with both SQLite and PostgreSQL.
    op.execute(
        "UPDATE users "
        "SET username = 'user_' || CAST(id AS TEXT) "
        "WHERE username IS NULL"
    )

    # SQLite cannot reliably ALTER a column to NOT NULL through
    # a standard ALTER COLUMN statement. Batch mode recreates the
    # table when required and supports both SQLite and PostgreSQL.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "username",
            existing_type=sa.String(length=40),
            nullable=False,
        )

    # Create the unique index only if it does not already exist.
    inspector = sa.inspect(conn)
    indexes = {
        index["name"]
        for index in inspector.get_indexes("users")
    }

    if "ix_users_username" not in indexes:
        op.create_index(
            "ix_users_username",
            "users",
            ["username"],
            unique=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    indexes = {
        index["name"]
        for index in inspector.get_indexes("users")
    }

    if "ix_users_username" in indexes:
        op.drop_index("ix_users_username", table_name="users")

    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "username" in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("username")
