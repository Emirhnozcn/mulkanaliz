from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class PropertyType(Base):
    __tablename__ = "property_types"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    group_code: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    properties: Mapped[list["Property"]] = relationship(back_populates="property_type")
    __table_args__ = (CheckConstraint("group_code IN ('residential', 'land', 'farmland')", name="group_valid"),)


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_type_id: Mapped[int] = mapped_column(ForeignKey("property_types.id", ondelete="RESTRICT"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    land_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    parcel_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    property_type: Mapped[PropertyType] = relationship(back_populates="properties")
    location: Mapped["Location"] = relationship(back_populates="properties")
    residential_details: Mapped["ResidentialDetails | None"] = relationship(back_populates="property", cascade="all, delete-orphan", uselist=False)
    land_details: Mapped["LandDetails | None"] = relationship(back_populates="property", cascade="all, delete-orphan", uselist=False)
    farmland_details: Mapped["FarmlandDetails | None"] = relationship(back_populates="property", cascade="all, delete-orphan", uselist=False)
    listings: Mapped[list["Listing"]] = relationship(back_populates="property")
    sales: Mapped[list["SaleTransaction"]] = relationship(back_populates="property")

    __table_args__ = (
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="latitude_range"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="longitude_range"),
        CheckConstraint("land_area_m2 IS NULL OR land_area_m2 > 0", name="land_area_positive"),
        Index("ix_properties_location_type", "location_id", "property_type_id"),
    )


class ResidentialDetails(Base):
    __tablename__ = "residential_details"
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True)
    net_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    gross_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    room_count: Mapped[int | None] = mapped_column(SmallInteger)
    living_room_count: Mapped[int | None] = mapped_column(SmallInteger)
    building_age: Mapped[int | None] = mapped_column(SmallInteger)
    floor_number: Mapped[int | None] = mapped_column(SmallInteger)
    total_floors: Mapped[int | None] = mapped_column(SmallInteger)
    heating_type: Mapped[str | None] = mapped_column(String(40))
    building_condition: Mapped[str | None] = mapped_column(String(40))
    furnished: Mapped[bool | None] = mapped_column(Boolean)
    has_elevator: Mapped[bool | None] = mapped_column(Boolean)
    has_parking: Mapped[bool | None] = mapped_column(Boolean)
    has_balcony: Mapped[bool | None] = mapped_column(Boolean)
    bathroom_count: Mapped[int | None] = mapped_column(SmallInteger)
    building_year: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    property: Mapped[Property] = relationship(back_populates="residential_details")
    __table_args__ = (
        CheckConstraint("net_area_m2 IS NULL OR net_area_m2 > 0", name="net_area_positive"),
        CheckConstraint("gross_area_m2 IS NULL OR gross_area_m2 > 0", name="gross_area_positive"),
        CheckConstraint("room_count IS NULL OR room_count > 0", name="room_count_positive"),
        CheckConstraint("building_age IS NULL OR building_age >= 0", name="building_age_nonnegative"),
        Index("ix_residential_details_room_count", "room_count"),
    )


class LandDetails(Base):
    __tablename__ = "land_details"
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True)
    parcel_area_m2: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    zoning_use: Mapped[str | None] = mapped_column(String(40))
    zoning_status: Mapped[str | None] = mapped_column(String(30))
    kaks: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    taks: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    max_building_floors: Mapped[int | None] = mapped_column(SmallInteger)
    frontage_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    road_access: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    property: Mapped[Property] = relationship(back_populates="land_details")
    __table_args__ = (
        CheckConstraint("parcel_area_m2 > 0", name="parcel_area_positive"),
        CheckConstraint("kaks IS NULL OR kaks >= 0", name="kaks_nonnegative"),
        CheckConstraint("taks IS NULL OR taks >= 0", name="taks_nonnegative"),
        Index("ix_land_details_zoning_use", "zoning_use"),
    )


class FarmlandDetails(Base):
    __tablename__ = "farmland_details"
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True)
    parcel_area_m2: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    land_quality: Mapped[str | None] = mapped_column(String(40))
    irrigation_available: Mapped[bool | None] = mapped_column(Boolean)
    road_access: Mapped[bool | None] = mapped_column(Boolean)
    electricity_available: Mapped[bool | None] = mapped_column(Boolean)
    water_source: Mapped[str | None] = mapped_column(String(40))
    slope_category: Mapped[str | None] = mapped_column(String(30))
    soil_type: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    property: Mapped[Property] = relationship(back_populates="farmland_details")
    __table_args__ = (CheckConstraint("parcel_area_m2 > 0", name="parcel_area_positive"),)
