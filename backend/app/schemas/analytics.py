from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

AreaType = Literal["net", "gross", "parcel"]
GroupBy = Literal["property_type", "neighborhood", "room_count", "building_age", "area_band", "zoning_status", "zoning_use"]


class PriceBucket(BaseModel):
    lower_bound: Decimal
    upper_bound: Decimal | None
    count: int


class AreaPriceMetric(BaseModel):
    area_type: AreaType
    listing_count: int
    average_price_per_m2: Decimal | None
    median_price_per_m2: Decimal | None


class ObservedPriceChange(BaseModel):
    listings_with_multiple_snapshots: int
    average_observed_change: Decimal | None
    average_observed_change_percent: Decimal | None
    earliest_snapshot_at: datetime | None
    latest_snapshot_at: datetime | None
    interpretation: str = "Yalnızca sistemde kayıtlı fiyat gözlemlerini karşılaştırır; ilk yayın fiyatı veya gerçekleşmiş satış fiyatı değildir."


class PriceSummary(BaseModel):
    filters: dict[str, object]
    currency: str
    listing_count: int
    average_asking_price: Decimal | None
    median_asking_price: Decimal | None
    minimum_asking_price: Decimal | None
    maximum_asking_price: Decimal | None
    area_price_metrics: list[AreaPriceMetric]
    price_distribution: list[PriceBucket]
    observed_price_change: ObservedPriceChange
    last_data_updated_at: datetime | None
    minimum_listings_threshold: int
    reliability: Literal["limited", "threshold_met"]
    reliability_note: str
    price_basis: str = "İlan fiyatı (asking price); gerçekleşmiş satış fiyatı değildir."
    model_config = ConfigDict(from_attributes=True)


class ComparisonRow(BaseModel):
    group_key: str
    group_label: str
    listing_count: int
    average_asking_price: Decimal | None
    median_asking_price: Decimal | None
    minimum_asking_price: Decimal | None
    maximum_asking_price: Decimal | None
    average_price_per_m2: Decimal | None
    median_price_per_m2: Decimal | None
    area_type: AreaType | None


class PriceComparison(BaseModel):
    group_by: GroupBy
    currency: str
    area_type_requested: AreaType
    groups: list[ComparisonRow]
    minimum_listings_threshold: int
    reliability_note: str
    price_basis: str = "İlan fiyatlarıdır; gerçekleşmiş satış fiyatları değildir."


from app.core.property_codes import RESIDENTIAL_LAND_CODES


class AnalyticsFilters(BaseModel):
    property_type: str | None = Field(default=None, min_length=1, max_length=40)
    province_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    neighborhood_id: int | None = Field(default=None, gt=0)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    min_net_area_m2: Decimal | None = Field(default=None, gt=0)
    max_net_area_m2: Decimal | None = Field(default=None, gt=0)
    min_gross_area_m2: Decimal | None = Field(default=None, gt=0)
    max_gross_area_m2: Decimal | None = Field(default=None, gt=0)
    min_parcel_area_m2: Decimal | None = Field(default=None, gt=0)
    max_parcel_area_m2: Decimal | None = Field(default=None, gt=0)
    room_count: int | None = Field(default=None, ge=1, le=30)
    min_building_age: int | None = Field(default=None, ge=0, le=300)
    max_building_age: int | None = Field(default=None, ge=0, le=300)
    zoning_status: str | None = Field(default=None, min_length=1, max_length=30)
    zoning_use: str | None = Field(default=None, min_length=1, max_length=40)
    currency: str = Field(default="TRY", min_length=3, max_length=3, pattern="^[A-Z]{3}$")

    @model_validator(mode="after")
    def validate_ranges(self):
        pairs = [
            ("min_price", "max_price"),
            ("min_net_area_m2", "max_net_area_m2"),
            ("min_gross_area_m2", "max_gross_area_m2"),
            ("min_parcel_area_m2", "max_parcel_area_m2"),
            ("min_building_age", "max_building_age"),
        ]
        for low, high in pairs:
            if getattr(self, low) is not None and getattr(self, high) is not None and getattr(self, low) > getattr(self, high):
                raise ValueError(f"{low}, {high} değerinden büyük olamaz.")
        if self.property_type and (self.zoning_status or self.zoning_use) and self.property_type not in RESIDENTIAL_LAND_CODES:
            raise ValueError("İmar filtreleri yalnızca imarlı arsa türüyle kullanılabilir.")
        return self
