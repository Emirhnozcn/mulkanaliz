from typing import Literal
from decimal import Decimal
from statistics import median
from sqlalchemy import select
from app.models.location import Location
from app.models.listing import Listing
from app.models.property import Property, PropertyType, ResidentialDetails, LandDetails, FarmlandDetails
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.property_codes import RESIDENTIAL_CODES, RESIDENTIAL_LAND_CODES, code_aliases
from app.db.session import get_db
from app.schemas.analytics import AnalyticsFilters, PriceComparison, PriceSummary
from app.services.analytics_service import get_price_comparison, get_price_summary

router = APIRouter()


def get_analytics_filters(
    property_type: str | None = Query(default=None, min_length=1, max_length=40),
    province_id: int | None = Query(default=None, gt=0),
    district_id: int | None = Query(default=None, gt=0),
    neighborhood_id: int | None = Query(default=None, gt=0),
    min_price: str | None = Query(default=None),
    max_price: str | None = Query(default=None),
    min_net_area_m2: str | None = Query(default=None),
    max_net_area_m2: str | None = Query(default=None),
    min_gross_area_m2: str | None = Query(default=None),
    max_gross_area_m2: str | None = Query(default=None),
    min_parcel_area_m2: str | None = Query(default=None),
    max_parcel_area_m2: str | None = Query(default=None),
    room_count: int | None = Query(default=None, ge=1, le=30),
    min_building_age: int | None = Query(default=None, ge=0, le=300),
    max_building_age: int | None = Query(default=None, ge=0, le=300),
    zoning_status: str | None = Query(default=None, min_length=1, max_length=30),
    zoning_use: str | None = Query(default=None, min_length=1, max_length=40),
    currency: str = Query(default="TRY", min_length=3, max_length=3, pattern="^[A-Z]{3}$"),
) -> AnalyticsFilters:
    values = locals().copy()
    try:
        return AnalyticsFilters.model_validate(values)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors(include_url=False))) from exc


@router.get("/price-summary", response_model=PriceSummary)
def price_summary(
    filters: AnalyticsFilters = Depends(get_analytics_filters),
    area_type: Literal["net", "gross"] = Query(default="net", description="Konut m² metriğinde kullanılacak alan. Arsa ve tarla için parsel alanı kullanılır."),
    minimum_listings: int = Query(default=5, ge=1, le=100, description="Yalnızca yorumlama uyarısı için yapılandırılabilir eşik; istatistiksel güvence değildir."),
    bucket_count: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> PriceSummary:
    """Fiyat istatistiklerini yalnızca eşleşen, aktif ve arşivlenmemiş ilanlardan hesaplar."""
    return get_price_summary(db, filters, area_type, minimum_listings, bucket_count)


@router.get("/compare", response_model=PriceComparison)
def compare_prices(
    filters: AnalyticsFilters = Depends(get_analytics_filters),
    group_by: Literal["property_type", "neighborhood", "room_count", "building_age", "area_band", "zoning_status", "zoning_use"] = Query(...),
    area_type: Literal["net", "gross"] = Query(default="net"),
    minimum_listings: int = Query(default=5, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PriceComparison:
    """İstenen kriterle gruplandırılmış fiyat karşılaştırması; m² türleri birbirine karıştırılmaz."""
    if group_by == "property_type" and filters.property_type is not None:
        raise HTTPException(status_code=422, detail="property_type karşılaştırmasında property_type filtresi verilmemelidir.")
    if group_by != "property_type" and filters.property_type is None:
        raise HTTPException(status_code=422, detail="Gayrimenkul türlerini karıştırmamak için property_type filtresi zorunludur.")
    if group_by in {"room_count", "building_age"} and filters.property_type not in {"apartment", "detached_house", "villa"}:
        raise HTTPException(status_code=422, detail="Oda sayısı ve bina yaşı karşılaştırması konut türleriyle yapılmalıdır.")
    if group_by in {"zoning_status", "zoning_use"} and filters.property_type not in RESIDENTIAL_LAND_CODES:
        raise HTTPException(status_code=422, detail="İmar karşılaştırması property_type=residential_zoned_land (veya residential_land) ile yapılmalıdır.")
    return get_price_comparison(db, filters, group_by, area_type, minimum_listings)


@router.get("/valuation")
def estimate_valuation(
    province_id: int = Query(..., gt=0),
    district_id: int = Query(..., gt=0),
    neighborhood_id: int = Query(..., gt=0),
    property_type: str = Query(..., min_length=1, max_length=40),
    area_m2: Decimal = Query(..., gt=0, le=1000000),
    area_type: Literal["net", "gross", "parcel"] = Query(default="net"),
    room_count: int | None = Query(default=None, ge=1, le=30, description="Toplam oda sayısı (2+1 = 3)."),
    db: Session = Depends(get_db),
):
    """Return separate sale and monthly-rent estimates from matching active asking listings.

    Emsal sırası: mahalle -> ilçe. Her seviyede önce alan (±%30) ve oda eşleşmesi, yetersizse oda, sonra alan
    kısıtı gevşetilir. Aşırı uç (hatalı girilmiş) fiyatlar medyana göre ayıklanır.
    """
    province = db.get(Location, province_id)
    district = db.get(Location, district_id)
    neighborhood = db.get(Location, neighborhood_id)
    if not province or province.level != "province" or not district or district.level != "district" or district.parent_id != province_id or not neighborhood or neighborhood.level != "neighborhood" or neighborhood.parent_id != district_id:
        raise HTTPException(status_code=422, detail="İl, ilçe ve mahalle seçimleri birbiriyle uyumlu olmalıdır.")

    aliases = code_aliases(property_type)
    type_row = db.scalar(select(PropertyType).where(PropertyType.code.in_(aliases)))
    if type_row is None:
        raise HTTPException(status_code=422, detail="Geçersiz gayrimenkul türü.")
    group = type_row.group_code
    if group == "residential":
        area_column = ResidentialDetails.net_area_m2 if area_type != "gross" else ResidentialDetails.gross_area_m2
        details_model = ResidentialDetails
    elif group == "farmland":
        area_column, details_model, area_type = FarmlandDetails.parcel_area_m2, FarmlandDetails, "parcel"
    else:
        area_column, details_model, area_type = LandDetails.parcel_area_m2, LandDetails, "parcel"
    use_rooms = group == "residential" and room_count is not None
    district_neighborhood_ids = select(Location.id).where(Location.parent_id == district_id, Location.level == "neighborhood")

    def estimate_for(transaction_type: str):
        label = "satılık" if transaction_type == "sale" else "kiralık"
        room_column = ResidentialDetails.room_count if group == "residential" else None
        columns = [Listing.asking_price, area_column] + ([room_column] if room_column is not None else [])
        base = (select(*columns)
            .join(Property, Listing.property_id == Property.id)
            .join(PropertyType, Property.property_type_id == PropertyType.id)
            .join(details_model, details_model.property_id == Property.id)
            .where(Listing.transaction_type == transaction_type, Listing.status == "active", Listing.archived_at.is_(None), Property.archived_at.is_(None), Listing.currency == "TRY", PropertyType.code.in_(aliases), area_column.is_not(None), area_column > 0, Listing.asking_price > 0))
        if room_column is None:
            def fetch(where):
                return [(Decimal(p), Decimal(a), None) for p, a in db.execute(base.where(where)).all()]
        else:
            def fetch(where):
                return [(Decimal(p), Decimal(a), r) for p, a, r in db.execute(base.where(where)).all()]
        by_level = {"neighborhood": fetch(Property.location_id == neighborhood_id), "district": fetch(Property.location_id.in_(district_neighborhood_ids))}

        low_bound, high_bound = area_m2 * Decimal("0.70"), area_m2 * Decimal("1.30")

        def pick(rows, band: bool, rooms: bool):
            return [(p, a) for p, a, r in rows
                    if (not band or low_bound <= a <= high_bound) and (not rooms or r is None or r == room_count)]

        def trim_outliers(items):
            # Yanlış girilmiş (ör. 7 TL'lik arsa) veya aşırı uç m² fiyatlarını medyana göre ayıkla.
            if len(items) < 4:
                return items
            mid = median(p / a for p, a in items)
            kept = [(p, a) for p, a in items if mid / 4 <= p / a <= mid * 4]
            return kept if len(kept) >= 3 else items

        # (seviye, alan bandı, oda kısıtı, açıklama) - ilk yeterli (>=3 emsal) sonuç kullanılır.
        plans = []
        for level in ("neighborhood", "district"):
            if use_rooms:
                plans.append((level, True, True, "alan ve oda sayısı benzer"))
            plans.append((level, True, False, "alan benzer"))
        plans.append(("district", False, False, "alan kısıtı gevşetilmiş"))
        chosen, source_level, basis = [], None, ""
        best = None
        for level, band, rooms, note in plans:
            comps = trim_outliers(pick(by_level[level], band, rooms))
            if len(comps) >= 3:
                chosen, source_level, basis = comps, level, note
                break
            if comps and (best is None or len(comps) > len(best[0]) or (len(comps) == len(best[0]) and level == "neighborhood")):
                best = (comps, level, note)
        if not chosen and best is not None:
            chosen, source_level, basis = best
        if not chosen:
            return {"transaction_type": transaction_type, "comparable_count": 0, "source_level": None, "estimated_price": None, "low_estimate": None, "high_estimate": None, "median_price_per_m2": None, "comparable_listings": [], "reliability": "no_data", "message": f"Bu bölgede {label} emsal ilan bulunamadı; tahmin üretilmedi."}
        per_m2 = [price / size for price, size in chosen]
        median_m2 = median(per_m2)
        estimated = median_m2 * area_m2
        reliability = "moderate" if len(chosen) >= 5 and source_level == "neighborhood" else "limited"
        where = "Mahalledeki" if source_level == "neighborhood" else "Aynı ilçedeki"
        message = (f"{where} {len(chosen)} aktif emsal ilanın ({basis}) medyan m² fiyatı kullanıldı."
                   + (" Mahallede yeterli emsal olmadığı için ilçe verisine genişletildi." if source_level == "district" else "")
                   + (" Emsal sayısı az olduğu için tahmin sınırlı güvenilirliktedir." if len(chosen) < 3 else "")
                   + (" Aylık kira ilanlarına dayalı tahmindir." if transaction_type == "rent" else " Satılık ilan fiyatlarına dayalı tahmindir.")
                   + " Gerçekleşmiş işlem fiyatı veya resmî ekspertiz değildir.")
        return {"transaction_type": transaction_type, "comparable_count": len(chosen), "source_level": source_level, "estimated_price": round(float(estimated), 2), "low_estimate": round(float(estimated * Decimal("0.90")), 2), "high_estimate": round(float(estimated * Decimal("1.10")), 2), "median_price_per_m2": round(float(median_m2), 2),
                "comparable_listings": [{"asking_price": float(price), "area_m2": float(size), "price_per_m2": round(float(price / size), 2)} for price, size in chosen[:20]],
                "reliability": reliability, "message": message}

    sale = estimate_for("sale")
    rent = estimate_for("rent")
    return {"province": province.name, "district": district.name, "neighborhood": neighborhood.name, "property_type": property_type, "area_m2": float(area_m2), "area_type": area_type, "sale_estimate": sale, "rent_estimate": rent,
        # Backward-compatible top-level fields point to the sale estimate.
        "transaction_type": "sale", "comparable_count": sale["comparable_count"], "source_level": sale["source_level"], "estimated_price": sale["estimated_price"], "low_estimate": sale["low_estimate"], "high_estimate": sale["high_estimate"], "median_price_per_m2": sale["median_price_per_m2"], "comparable_listings": sale["comparable_listings"], "reliability": sale["reliability"], "message": sale["message"]}
