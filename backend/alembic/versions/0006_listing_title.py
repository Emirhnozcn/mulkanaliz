"""Add human-readable title to listings.

Revision ID: 0006_listing_title
Revises: 0005_residential_floors
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_listing_title"
down_revision: Union[str, None] = "0005_residential_floors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "title" not in {c["name"] for c in inspector.get_columns("listings")}:
        op.add_column("listings", sa.Column("title", sa.String(length=300), nullable=True))

def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "title" in {c["name"] for c in inspector.get_columns("listings")}:
        op.drop_column("listings", "title")
