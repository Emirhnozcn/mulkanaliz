from datetime import datetime
from decimal import Decimal
from typing import Literal, Self
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

PropertyCode = Literal[
    "apartment", "detached_house", "villa",
    "residential_zoned_land", "commercial_zoned_land", "farmland",
]


class ImportListingRequest(BaseModel):
    """User-confirmed data extracted from a page the user is authorized to access."""
    source_url: HttpUrl
    source_name: str = Field(min_length=1, max_length=100)
    source_listing_id: str | None = Field(default=None, max_length=150)
    created_by: int | None = Field(default=None, gt=0, description="Sunucu tarafından oturum kullanıcısıyla değiştirilir.")
    location_id: int = Field(gt=0, description="Önceden tanımlı il/ilçe/mahalle kaydı.")
    property_type_code: PropertyCode
    transaction_type: Literal["sale", "rent"] = "sale"
    asking_price: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    title: str | None = Field(default=None, max_length=300)
    address: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=5000)
    net_area_m2: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    gross_area_m2: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    room_count: int | None = Field(default=None, ge=1, le=30)
    living_room_count: int | None = Field(default=None, ge=0, le=10, description="2+1 gibi düzenlerde salon sayısı (room_count toplam oda).")
    building_age: int | None = Field(default=None, ge=0, le=300)
    floor_number: int | None = Field(default=None, ge=-10, le=300)
    total_floors: int | None = Field(default=None, ge=1, le=300)
    parcel_area_m2: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    zoning_status: str | None = Field(default=None, max_length=30)
    zoning_use: str | None = Field(default=None, max_length=40)
    published_at: datetime | None = None

    @model_validator(mode="after")
    def area_fields_match_property_type(self) -> Self:
        residential = self.property_type_code in {"apartment", "detached_house", "villa"}
        land = self.property_type_code in {"residential_zoned_land", "commercial_zoned_land", "farmland"}
        if residential and self.parcel_area_m2 is not None:
            raise ValueError("Konut aktarımında parcel_area_m2 kullanılamaz.")
        if land and any(v is not None for v in (self.net_area_m2, self.gross_area_m2, self.room_count, self.living_room_count, self.building_age, self.floor_number, self.total_floors)):
            raise ValueError("Arsa/tarla aktarımında konut alanları, oda sayısı ve bina yaşı kullanılamaz.")
        if land and self.parcel_area_m2 is None:
            raise ValueError("Arsa/tarla aktarımında parcel_area_m2 zorunludur.")
        if self.property_type_code == "farmland" and (self.zoning_status or self.zoning_use):
            raise ValueError("Tarla aktarımında imar durumu/kullanımı arsa alanları gibi kabul edilmez.")
        if self.source_listing_id and not self.source_name:
            raise ValueError("Harici ilan kimliği için kaynak adı zorunludur.")
        return self


class ImportListingResult(BaseModel):
    listing_id: int
    property_id: int
    action: Literal["created", "updated", "unchanged"]
    price_changed: bool
    message: str
    model_config = ConfigDict(from_attributes=True)
