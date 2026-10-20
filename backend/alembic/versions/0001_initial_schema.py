"""Initial schema for real estate analytics.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("normalized_name", sa.String(150), nullable=False),
        sa.Column("external_code", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["locations.id"], name="fk_locations_parent_id_locations", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_locations"),
        sa.CheckConstraint("level IN ('province', 'district', 'neighborhood')", name="level_valid"),
    )
    op.create_index("ix_locations_parent_normalized_name", "locations", ["parent_id", "normalized_name"])
    op.create_index("uq_locations_external_code", "locations", ["external_code"], unique=True, postgresql_where=sa.text("external_code IS NOT NULL"))

    op.create_table("property_types",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("group_code", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id", name="pk_property_types"),
        sa.UniqueConstraint("code", name="uq_property_types_code"),
        sa.CheckConstraint("group_code IN ('residential', 'land', 'farmland')", name="group_valid"),
    )

    op.bulk_insert(
        sa.table("property_types",
            sa.column("id", sa.SmallInteger()), sa.column("code", sa.String()),
            sa.column("name", sa.String()), sa.column("group_code", sa.String()),
            sa.column("is_active", sa.Boolean()),
        ),
        [
            {"id": 1, "code": "apartment", "name": "Daire", "group_code": "residential", "is_active": True},
            {"id": 2, "code": "detached_house", "name": "Müstakil Ev", "group_code": "residential", "is_active": True},
            {"id": 3, "code": "villa", "name": "Villa", "group_code": "residential", "is_active": True},
            {"id": 4, "code": "residential_zoned_land", "name": "Konut İmarlı Arsa", "group_code": "land", "is_active": True},
            {"id": 5, "code": "commercial_zoned_land", "name": "Ticari İmarlı Arsa", "group_code": "land", "is_active": True},
            {"id": 6, "code": "farmland", "name": "Tarla", "group_code": "farmland", "is_active": True},
        ],
    )

    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="agent"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('admin', 'agent')", name="role_valid"),
    )

    op.create_table("properties",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_type_id", sa.SmallInteger(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("land_area_m2", sa.Numeric(14, 2), nullable=True),
        sa.Column("parcel_number", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["property_type_id"], ["property_types.id"], name="fk_properties_property_type_id_property_types", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], name="fk_properties_location_id_locations", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_properties"),
        sa.CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="latitude_range"),
        sa.CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="longitude_range"),
        sa.CheckConstraint("land_area_m2 IS NULL OR land_area_m2 > 0", name="land_area_positive"),
    )
    op.create_index("ix_properties_location_type", "properties", ["location_id", "property_type_id"])

    op.create_table("residential_details",
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("net_area_m2", sa.Numeric(10, 2), nullable=True),
        sa.Column("gross_area_m2", sa.Numeric(10, 2), nullable=True),
        sa.Column("room_count", sa.SmallInteger(), nullable=True),
        sa.Column("living_room_count", sa.SmallInteger(), nullable=True),
        sa.Column("building_age", sa.SmallInteger(), nullable=True),
        sa.Column("floor_number", sa.SmallInteger(), nullable=True),
        sa.Column("total_floors", sa.SmallInteger(), nullable=True),
        sa.Column("heating_type", sa.String(40), nullable=True),
        sa.Column("building_condition", sa.String(40), nullable=True),
        sa.Column("furnished", sa.Boolean(), nullable=True),
        sa.Column("has_elevator", sa.Boolean(), nullable=True),
        sa.Column("has_parking", sa.Boolean(), nullable=True),
        sa.Column("has_balcony", sa.Boolean(), nullable=True),
        sa.Column("bathroom_count", sa.SmallInteger(), nullable=True),
        sa.Column("building_year", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_residential_details_property_id_properties", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id", name="pk_residential_details"),
        sa.CheckConstraint("net_area_m2 IS NULL OR net_area_m2 > 0", name="net_area_positive"),
        sa.CheckConstraint("gross_area_m2 IS NULL OR gross_area_m2 > 0", name="gross_area_positive"),
        sa.CheckConstraint("room_count IS NULL OR room_count > 0", name="room_count_positive"),
        sa.CheckConstraint("building_age IS NULL OR building_age >= 0", name="building_age_nonnegative"),
    )
    op.create_index("ix_residential_details_room_count", "residential_details", ["room_count"])

    op.create_table("land_details",
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("parcel_area_m2", sa.Numeric(14, 2), nullable=False),
        sa.Column("zoning_use", sa.String(40), nullable=True),
        sa.Column("zoning_status", sa.String(30), nullable=True),
        sa.Column("kaks", sa.Numeric(7, 4), nullable=True),
        sa.Column("taks", sa.Numeric(7, 4), nullable=True),
        sa.Column("max_building_floors", sa.SmallInteger(), nullable=True),
        sa.Column("frontage_m", sa.Numeric(10, 2), nullable=True),
        sa.Column("road_access", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_land_details_property_id_properties", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id", name="pk_land_details"),
        sa.CheckConstraint("parcel_area_m2 > 0", name="parcel_area_positive"),
        sa.CheckConstraint("kaks IS NULL OR kaks >= 0", name="kaks_nonnegative"),
        sa.CheckConstraint("taks IS NULL OR taks >= 0", name="taks_nonnegative"),
    )
    op.create_index("ix_land_details_zoning_use", "land_details", ["zoning_use"])

    op.create_table("farmland_details",
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("parcel_area_m2", sa.Numeric(14, 2), nullable=False),
        sa.Column("land_quality", sa.String(40), nullable=True),
        sa.Column("irrigation_available", sa.Boolean(), nullable=True),
        sa.Column("road_access", sa.Boolean(), nullable=True),
        sa.Column("electricity_available", sa.Boolean(), nullable=True),
        sa.Column("water_source", sa.String(40), nullable=True),
        sa.Column("slope_category", sa.String(30), nullable=True),
        sa.Column("soil_type", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_farmland_details_property_id_properties", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id", name="pk_farmland_details"),
        sa.CheckConstraint("parcel_area_m2 > 0", name="parcel_area_positive"),
    )

    op.create_table("listings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("source_name", sa.String(100), nullable=True),
        sa.Column("source_listing_id", sa.String(150), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("asking_price", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="TRY"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_listings_property_id_properties", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_listings_created_by_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_listings"),
        sa.CheckConstraint("asking_price > 0", name="asking_price_positive"),
        sa.CheckConstraint("length(currency) = 3", name="currency_length"),
        sa.CheckConstraint("status IN ('active', 'passive', 'sold', 'withdrawn')", name="status_valid"),
        sa.CheckConstraint("source_type IN ('manual', 'import', 'authorized_source')", name="source_type_valid"),
    )
    op.create_index("ix_listings_status_created_at", "listings", ["status", "created_at"])
    op.create_index("ix_listings_property_created_at", "listings", ["property_id", "created_at"])
    op.create_index("uq_listings_source_external_id", "listings", ["source_name", "source_listing_id"], unique=True, postgresql_where=sa.text("source_listing_id IS NOT NULL AND source_name IS NOT NULL"))

    op.create_table("listing_price_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("asking_price", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("change_reason", sa.String(30), nullable=False),
        sa.Column("recorded_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], name="fk_listing_price_history_listing_id_listings", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], name="fk_listing_price_history_recorded_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_listing_price_history"),
        sa.CheckConstraint("asking_price > 0", name="asking_price_positive"),
    )
    op.create_index("ix_price_history_listing_recorded_at", "listing_price_history", ["listing_id", "recorded_at"])

    op.create_table("sale_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("recorded_by", sa.Integer(), nullable=False),
        sa.Column("sale_price", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="TRY"),
        sa.Column("sale_date", sa.Date(), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_sale_transactions_property_id_properties", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], name="fk_sale_transactions_recorded_by_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_sale_transactions"),
        sa.CheckConstraint("sale_price > 0", name="sale_price_positive"),
        sa.CheckConstraint("verification_status IN ('unverified', 'documented', 'verified')", name="verification_status_valid"),
    )
    op.create_index("ix_sales_property_date", "sale_transactions", ["property_id", "sale_date"])


def downgrade() -> None:
    op.drop_index("ix_sales_property_date", table_name="sale_transactions")
    op.drop_table("sale_transactions")
    op.drop_index("ix_price_history_listing_recorded_at", table_name="listing_price_history")
    op.drop_table("listing_price_history")
    op.drop_index("uq_listings_source_external_id", table_name="listings")
    op.drop_index("ix_listings_property_created_at", table_name="listings")
    op.drop_index("ix_listings_status_created_at", table_name="listings")
    op.drop_table("listings")
    op.drop_index("ix_land_details_zoning_use", table_name="land_details")
    op.drop_table("farmland_details")
    op.drop_table("land_details")
    op.drop_index("ix_residential_details_room_count", table_name="residential_details")
    op.drop_table("residential_details")
    op.drop_index("ix_properties_location_type", table_name="properties")
    op.drop_table("properties")
    op.drop_table("users")
    op.drop_table("property_types")
    op.drop_index("uq_locations_external_code", table_name="locations")
    op.drop_index("ix_locations_parent_normalized_name", table_name="locations")
    op.drop_table("locations")
