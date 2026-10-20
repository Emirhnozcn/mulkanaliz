from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    source_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_listing_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False, default="sale", server_default="sale")
    asking_price: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TRY")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    property: Mapped["Property"] = relationship(back_populates="listings")
    created_by_user: Mapped["User"] = relationship(back_populates="listings")
    price_history: Mapped[list["ListingPriceHistory"]] = relationship(back_populates="listing", cascade="all, delete-orphan", order_by="ListingPriceHistory.recorded_at")

    __table_args__ = (
        CheckConstraint("transaction_type IN ('sale', 'rent')", name="listing_transaction_type_valid"),
        CheckConstraint("asking_price > 0", name="asking_price_positive"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        CheckConstraint("status IN ('active', 'passive', 'sold', 'withdrawn')", name="status_valid"),
        CheckConstraint("source_type IN ('manual', 'import', 'authorized_source')", name="source_type_valid"),
        Index("ix_listings_status_created_at", "status", "created_at"),
        Index("ix_listings_property_created_at", "property_id", "created_at"),
        Index("uq_listings_source_external_id", "source_name", "source_listing_id", unique=True, postgresql_where=(source_listing_id.is_not(None) & source_name.is_not(None))),
    )


class ListingPriceHistory(Base):
    __tablename__ = "listing_price_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    asking_price: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(30), nullable=False)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    listing: Mapped[Listing] = relationship(back_populates="price_history")
    __table_args__ = (
        CheckConstraint("asking_price > 0", name="asking_price_positive"),
        Index("ix_price_history_listing_recorded_at", "listing_id", "recorded_at"),
    )
