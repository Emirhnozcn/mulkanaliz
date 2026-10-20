from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ListingCreate(BaseModel):
    property_id: int = Field(gt=0)
    created_by: int | None = Field(default=None, gt=0, description="Sunucu tarafından oturum kullanıcısıyla belirlenir.")
    source_type: str = Field(default="manual", pattern="^(manual|import|authorized_source)$")
    source_name: str | None = Field(default=None, max_length=100)
    source_listing_id: str | None = Field(default=None, max_length=150)
    source_url: HttpUrl | None = None
    title: str | None = Field(default=None, max_length=300)
    transaction_type: str = Field(default="sale", pattern="^(sale|rent)$")
    asking_price: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    status: str = Field(default="active", pattern="^(active|passive|sold|withdrawn)$")
    published_at: datetime | None = None
    last_seen_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def source_id_requires_source(self) -> Self:
        if self.source_listing_id and not self.source_name:
            raise ValueError("Harici ilan kimliği kullanılıyorsa kaynak adı da zorunludur.")
        return self


class ListingUpdate(BaseModel):
    property_id: int | None = Field(default=None, gt=0)
    transaction_type: str | None = Field(default=None, pattern="^(sale|rent)$")
    asking_price: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    status: str | None = Field(default=None, pattern="^(active|passive|sold|withdrawn)$")
    source_url: HttpUrl | None = None
    title: str | None = Field(default=None, max_length=300)
    published_at: datetime | None = None
    last_seen_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def non_nullable_fields_cannot_be_null(self) -> Self:
        for field_name in ("property_id", "asking_price", "currency", "status", "transaction_type"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} alanı null olamaz.")
        return self


class ListingRead(BaseModel):
    id: int
    property_id: int
    created_by: int
    source_type: str
    source_name: str | None
    source_listing_id: str | None
    source_url: str | None
    title: str | None = None
    transaction_type: str
    asking_price: Decimal
    currency: str
    status: str
    published_at: datetime | None
    last_seen_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    # Ayırt edici özet alanları (liste/detay yanıtlarında doldurulur; diğer yanıtlarda boş kalır).
    province_name: str | None = None
    district_name: str | None = None
    neighborhood_name: str | None = None
    location_label: str | None = None
    property_type_code: str | None = None
    property_type_name: str | None = None
    room_count: int | None = None
    living_room_count: int | None = None
    room_label: str | None = None
    net_area_m2: Decimal | None = None
    gross_area_m2: Decimal | None = None
    parcel_area_m2: Decimal | None = None
    building_age: int | None = None
    floor_number: int | None = None
    total_floors: int | None = None
    model_config = ConfigDict(from_attributes=True)


class PriceHistoryRead(BaseModel):
    id: int
    listing_id: int
    asking_price: Decimal
    currency: str
    recorded_at: datetime
    change_reason: str
    recorded_by: int | None
    model_config = ConfigDict(from_attributes=True)
