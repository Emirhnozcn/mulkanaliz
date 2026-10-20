from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class SaleTransaction(Base):
    __tablename__ = "sale_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TRY")
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified")
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    property: Mapped["Property"] = relationship(back_populates="sales")
    __table_args__ = (
        CheckConstraint("sale_price > 0", name="sale_price_positive"),
        CheckConstraint("verification_status IN ('unverified', 'documented', 'verified')", name="verification_status_valid"),
        Index("ix_sales_property_date", "property_id", "sale_date"),
    )
