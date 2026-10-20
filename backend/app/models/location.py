from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(150), nullable=False)
    external_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    parent: Mapped["Location | None"] = relationship(remote_side="Location.id", back_populates="children")
    children: Mapped[list["Location"]] = relationship(back_populates="parent")
    properties: Mapped[list["Property"]] = relationship(back_populates="location")

    __table_args__ = (
        CheckConstraint("level IN ('province', 'district', 'neighborhood')", name="level_valid"),
        Index("ix_locations_parent_normalized_name", "parent_id", "normalized_name"),
        Index("uq_locations_external_code", "external_code", unique=True, postgresql_where=(external_code.is_not(None))),
    )
