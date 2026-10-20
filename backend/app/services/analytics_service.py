from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import and_, or_, select, func
from sqlalchemy.orm import Session, aliased

from app.core.property_codes import code_aliases
from app.models.listing import Listing, ListingPriceHistory
from app.models.location import Location
from app.models.property import Property, PropertyType, ResidentialDetails, LandDetails, FarmlandDetails
from app.schemas.analytics import AnalyticsFilters, PriceBucket, AreaPriceMetric, ObservedPriceChange, PriceSummary, ComparisonRow, PriceComparison

ZERO = Decimal("0")


def _base_rows(db: Session, filters: AnalyticsFilters):
    neighborhood = aliased(Location, name="analytics_neighborhood")
    district = aliased(Location, name="analytics_district")
    province = aliased(Location, name="analytics_province")
    stmt = (
        select(Listing, Property, PropertyType, neighborhood, ResidentialDetails, LandDetails, FarmlandDetails)
        .join(Property, Listing.property_id == Property.id)
        .join(PropertyType, Property.property_type_id == PropertyType.id)
        .outerjoin(ResidentialDetails, ResidentialDetails.property_id == Property.id)
        .outerjoin(LandDetails, LandDetails.property_id == Property.id)
        .outerjoin(FarmlandDetails, FarmlandDetails.property_id == Property.id)
        .outerjoin(neighborhood, and_(Property.location_id == neighborhood.id, neighborhood.level == "neighborhood"))
        .outerjoin(district, and_(district.level == "district", or_(Property.location_id == district.id, neighborhood.parent_id == district.id)))
        .outerjoin(province, and_(province.level == "province", or_(Property.location_id == province.id, district.parent_id == province.id)))
        .where(Listing.archived_at.is_(None), Property.archived_at.is_(None), Listing.status == "active", Listing.currency == filters.currency)
    )
    if filters.property_type:
        stmt = stmt.where(PropertyType.code.in_(code_aliases(filters.property_type)))
    if filters.province_id:
        stmt = stmt.where(province.id == filters.province_id)
    if filters.district_id:
        stmt = stmt.where(district.id == filters.district_id)
    if filters.neighborhood_id:
        stmt = stmt.where(neighborhood.id == filters.neighborhood_id)
    if filters.min_price is not None:
        stmt = stmt.where(Listing.asking_price >= filters.min_price)
    if filters.max_price is not None:
        stmt = stmt.where(Listing.asking_price <= filters.max_price)
    if filters.min_net_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.net_area_m2 >= filters.min_net_area_m2)
    if filters.max_net_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.net_area_m2 <= filters.max_net_area_m2)
    if filters.min_gross_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.gross_area_m2 >= filters.min_gross_area_m2)
    if filters.max_gross_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.gross_area_m2 <= filters.max_gross_area_m2)
    if filters.min_parcel_area_m2 is not None or filters.max_parcel_area_m2 is not None:
        land_area_conditions = []
        farmland_area_conditions = []
        if filters.min_parcel_area_m2 is not None:
            land_area_conditions.append(LandDetails.parcel_area_m2 >= filters.min_parcel_area_m2)
            farmland_area_conditions.append(FarmlandDetails.parcel_area_m2 >= filters.min_parcel_area_m2)
        if filters.max_parcel_area_m2 is not None:
            land_area_conditions.append(LandDetails.parcel_area_m2 <= filters.max_parcel_area_m2)
            farmland_area_conditions.append(FarmlandDetails.parcel_area_m2 <= filters.max_parcel_area_m2)
        stmt = stmt.where(or_(and_(*land_area_conditions), and_(*farmland_area_conditions)))
    if filters.room_count is not None:
        stmt = stmt.where(ResidentialDetails.room_count == filters.room_count)
    if filters.min_building_age is not None:
        stmt = stmt.where(ResidentialDetails.building_age >= filters.min_building_age)
    if filters.max_building_age is not None:
        stmt = stmt.where(ResidentialDetails.building_age <= filters.max_building_age)
    if filters.zoning_status is not None:
        stmt = stmt.where(PropertyType.group_code == "land", LandDetails.zoning_status == filters.zoning_status)
    if filters.zoning_use is not None:
        stmt = stmt.where(PropertyType.group_code == "land", LandDetails.zoning_use == filters.zoning_use)
    return db.execute(stmt.distinct()).all()


def _area(item, area_type: str) -> tuple[Decimal | None, str | None]:
    listing, prop, property_type, _neighborhood, residential, land, farmland = item
    if property_type.group_code == "residential":
        if residential is None:
            return None, None
        field = residential.net_area_m2 if area_type == "net" else residential.gross_area_m2 if area_type == "gross" else None
        return (Decimal(field) if field is not None else None, area_type if field is not None else None)
    if property_type.group_code == "land":
        field = land.parcel_area_m2 if land else None
        return (Decimal(field) if field is not None else None, "parcel" if field is not None else None)
    if property_type.group_code == "farmland":
        field = farmland.parcel_area_m2 if farmland else None
        return (Decimal(field) if field is not None else None, "parcel" if field is not None else None)
    return None, None


def _metrics(items: list[tuple], area_type: str, min_count: int) -> dict[str, Any]:
    prices = [Decimal(item[0].asking_price) for item in items]
    average = sum(prices, ZERO) / len(prices) if prices else None
    med = median(prices) if prices else None
    areas_by_type: dict[str, list[Decimal]] = defaultdict(list)
    price_m2_by_type: dict[str, list[Decimal]] = defaultdict(list)
    updated: list[datetime] = []
    for item in items:
        listing, prop, _ptype, _neighborhood, residential, land, farmland = item
        area, actual_type = _area(item, area_type)
        if area and actual_type:
            areas_by_type[actual_type].append(area)
            price_m2_by_type[actual_type].append(Decimal(listing.asking_price) / area)
        for stamp in (listing.updated_at, prop.updated_at, getattr(residential, "updated_at", None), getattr(land, "updated_at", None), getattr(farmland, "updated_at", None)):
            if stamp:
                updated.append(stamp)
    area_metrics = [AreaPriceMetric(area_type=key, listing_count=len(values), average_price_per_m2=sum(price_m2_by_type[key], ZERO) / len(price_m2_by_type[key]), median_price_per_m2=median(price_m2_by_type[key])) for key, values in sorted(areas_by_type.items()) if price_m2_by_type[key]]
    return {"prices": prices, "average": average, "median": med, "minimum": min(prices) if prices else None, "maximum": max(prices) if prices else None,
            "area_metrics": area_metrics, "last_updated": max(updated) if updated else None, "count": len(items)}


def _distribution(prices: list[Decimal], bucket_count: int) -> list[PriceBucket]:
    if not prices:
        return []
    low, high = min(prices), max(prices)
    if low == high:
        return [PriceBucket(lower_bound=low, upper_bound=None, count=len(prices))]
    width = (high - low) / Decimal(bucket_count)
    counts = [0] * bucket_count
    for price in prices:
        index = min(int((price - low) / width), bucket_count - 1)
        counts[index] += 1
    return [PriceBucket(lower_bound=low + width * i, upper_bound=low + width * (i + 1) if i < bucket_count - 1 else None, count=counts[i]) for i in range(bucket_count)]


def _history_change(db: Session, items: list[tuple]) -> ObservedPriceChange:
    listing_ids = [item[0].id for item in items]
    if not listing_ids:
        return ObservedPriceChange(listings_with_multiple_snapshots=0, average_observed_change=None, average_observed_change_percent=None, earliest_snapshot_at=None, latest_snapshot_at=None)
    histories = db.scalars(select(ListingPriceHistory).where(ListingPriceHistory.listing_id.in_(listing_ids)).order_by(ListingPriceHistory.listing_id, ListingPriceHistory.recorded_at, ListingPriceHistory.id)).all()
    grouped: dict[int, list] = defaultdict(list)
    for h in histories:
        grouped[h.listing_id].append(h)
    deltas, percents, dates = [], [], []
    for snapshots in grouped.values():
        dates.extend(h.recorded_at for h in snapshots)
        if len(snapshots) >= 2:
            first, last = snapshots[0], snapshots[-1]
            if first.currency == last.currency and first.asking_price > 0:
                change = Decimal(last.asking_price) - Decimal(first.asking_price)
                deltas.append(change)
                percents.append(change / Decimal(first.asking_price) * Decimal("100"))
    return ObservedPriceChange(
        listings_with_multiple_snapshots=len(deltas),
        average_observed_change=sum(deltas, ZERO) / len(deltas) if deltas else None,
        average_observed_change_percent=sum(percents, ZERO) / len(percents) if percents else None,
        earliest_snapshot_at=min(dates) if dates else None,
        latest_snapshot_at=max(dates) if dates else None,
    )


def get_price_summary(db: Session, filters: AnalyticsFilters, area_type: str = "net", minimum_listings: int = 5, bucket_count: int = 5) -> PriceSummary:
    items = _base_rows(db, filters)
    metrics = _metrics(items, area_type, minimum_listings)
    history = _history_change(db, items)
    if history.latest_snapshot_at and (metrics["last_updated"] is None or history.latest_snapshot_at > metrics["last_updated"]):
        metrics["last_updated"] = history.latest_snapshot_at
    reliable = metrics["count"] >= minimum_listings
    note = (f"Eşleşen {metrics['count']} ilan, yapılandırılmış {minimum_listings} ilan eşiğini karşılıyor; bu tek başına istatistiksel güvence değildir." if reliable else f"Yalnızca {metrics['count']} ilan eşleşti; yapılandırılmış {minimum_listings} ilan eşiğinin altında olduğu için sonuçlar sınırlı güvenilirliktedir. Bu eşik istatistiksel güvence değildir.")
    return PriceSummary(filters={**filters.model_dump(exclude_none=True), "area_type": area_type, "minimum_listings": minimum_listings, "bucket_count": bucket_count}, currency=filters.currency, listing_count=metrics["count"], average_asking_price=metrics["average"], median_asking_price=metrics["median"], minimum_asking_price=metrics["minimum"], maximum_asking_price=metrics["maximum"], area_price_metrics=metrics["area_metrics"], price_distribution=_distribution(metrics["prices"], bucket_count), observed_price_change=history, last_data_updated_at=metrics["last_updated"], minimum_listings_threshold=minimum_listings, reliability="threshold_met" if reliable else "limited", reliability_note=note)


def get_price_comparison(db: Session, filters: AnalyticsFilters, group_by: str, area_type: str, minimum_listings: int) -> PriceComparison:
    items = _base_rows(db, filters)
    groups: dict[str, list[tuple]] = defaultdict(list)
    labels: dict[str, str] = {}
    for item in items:
        listing, prop, ptype, neighborhood, residential, land, farmland = item
        if group_by == "property_type":
            key, label = ptype.code, ptype.name
        elif group_by == "neighborhood":
            key, label = (str(neighborhood.id), neighborhood.name) if neighborhood else ("unknown", "Mahalle bilgisi yok")
        elif group_by == "room_count":
            key, label = (str(residential.room_count), f"{residential.room_count} oda") if residential and residential.room_count is not None else ("unknown", "Oda sayısı bilinmiyor")
        elif group_by == "building_age":
            age = residential.building_age if residential else None
            if age is None: key, label = "unknown", "Bina yaşı bilinmiyor"
            elif age <= 5: key, label = "0-5", "0-5 yıl"
            elif age <= 10: key, label = "6-10", "6-10 yıl"
            elif age <= 20: key, label = "11-20", "11-20 yıl"
            else: key, label = "21+", "21 yıl ve üzeri"
        elif group_by == "area_band":
            area, _ = _area(item, area_type)
            if area is None: key, label = "unknown", "Alan bilgisi bilinmiyor"
            elif area <= 50: key, label = "0-50", "50 m² ve altı"
            elif area <= 100: key, label = "51-100", "51-100 m²"
            elif area <= 150: key, label = "101-150", "101-150 m²"
            elif area <= 250: key, label = "151-250", "151-250 m²"
            else: key, label = "251+", "250 m² üzeri"
        elif group_by == "zoning_status":
            key, label = (land.zoning_status, land.zoning_status) if land and land.zoning_status else ("unknown", "İmar durumu bilinmiyor")
        else:
            key, label = (land.zoning_use, land.zoning_use) if land and land.zoning_use else ("unknown", "İmar kullanım amacı bilinmiyor")
        groups[key].append(item); labels[key] = label
    rows = []
    for key, group in groups.items():
        m = _metrics(group, area_type, minimum_listings)
        # Do not calculate a single m² metric for mixed area types.
        actual_types = {metric.area_type for metric in m["area_metrics"]}
        single_area_type = next(iter(actual_types)) if len(actual_types) == 1 else None
        per_m2 = m["area_metrics"][0] if len(m["area_metrics"]) == 1 else None
        rows.append(ComparisonRow(group_key=key, group_label=labels[key], listing_count=m["count"], average_asking_price=m["average"], median_asking_price=m["median"], minimum_asking_price=m["minimum"], maximum_asking_price=m["maximum"], average_price_per_m2=per_m2.average_price_per_m2 if per_m2 else None, median_price_per_m2=per_m2.median_price_per_m2 if per_m2 else None, area_type=single_area_type))
    rows.sort(key=lambda r: (r.group_key == "unknown", r.group_key))
    note = f"Gruplar en az {minimum_listings} ilan eşiğine göre yorumlanmalıdır; eşik istatistiksel güvence değildir. Farklı gayrimenkul türleri veya alan ölçüleri aynı m² metriğinde birleştirilmez."
    return PriceComparison(group_by=group_by, currency=filters.currency, area_type_requested=area_type, groups=rows, minimum_listings_threshold=minimum_listings, reliability_note=note)
