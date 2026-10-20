from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field, HttpUrl
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from app.api.dependencies import get_current_user
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.errors import ConflictError, NotFoundError
from app.core.property_codes import code_aliases
from app.db.session import get_db
from app.models.listing import Listing, ListingPriceHistory
from app.models.user import User
from app.models.location import Location
from app.models.property import (
    FarmlandDetails,
    LandDetails,
    Property,
    PropertyType,
    ResidentialDetails,
)
from app.schemas.listing import ListingCreate, ListingRead, ListingUpdate, PriceHistoryRead
from app.services.listing_service import create_listing, listing_summaries, update_listing

router = APIRouter()


class QuickListingCreate(BaseModel):
    property_type: str = Field(min_length=1, max_length=40)
    location_id: int = Field(gt=0)
    address: str | None = None
    has_parking: bool | None = None
    transaction_type: str = Field(default="sale", pattern="^(sale|rent)$")
    asking_price: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    status: str = Field(default="active", pattern="^(active|passive|sold|withdrawn)$")
    source_type: str = Field(default="manual", pattern="^(manual|import|authorized_source)$")
    source_name: str | None = Field(default=None, max_length=100)
    source_listing_id: str | None = Field(default=None, max_length=150)
    source_url: HttpUrl | None = None
    title: str | None = Field(default=None, max_length=300)
    published_at: datetime | None = None
    notes: str | None = None


@router.post("/quick-create", response_model=ListingRead, status_code=201)
def quick_create_listing(payload: QuickListingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create property, listing and first price snapshot using the authenticated user."""
    location = db.get(Location, payload.location_id)
    if location is None or location.level != "neighborhood":
        raise HTTPException(status_code=422, detail="Geçerli bir mahalle seçilmelidir.")
    prop_type = db.scalar(select(PropertyType).where(PropertyType.code == payload.property_type, PropertyType.is_active.is_(True)))
    if prop_type is None:
        raise HTTPException(status_code=422, detail="Geçersiz gayrimenkul türü.")
    if payload.source_listing_id and not payload.source_name:
        raise HTTPException(status_code=422, detail="İlan numarası girildiğinde kaynak adı da gereklidir.")
    if payload.source_listing_id and db.scalar(select(Listing.id).where(Listing.source_name == payload.source_name, Listing.source_listing_id == payload.source_listing_id)) is not None:
        raise HTTPException(status_code=409, detail="Bu kaynak ilan numarası zaten kayıtlı.")
    try:
        prop = Property(property_type_id=prop_type.id, location_id=location.id, address=payload.address)
        db.add(prop)
        db.flush()
        if prop_type.group_code == "residential" and payload.has_parking is not None:
            db.add(ResidentialDetails(property_id=prop.id, has_parking=payload.has_parking))
        listing = Listing(property_id=prop.id, created_by=current_user.id, source_type=payload.source_type,
            source_name=payload.source_name, source_listing_id=payload.source_listing_id,
            source_url=str(payload.source_url) if payload.source_url else None, title=payload.title, transaction_type=payload.transaction_type, asking_price=payload.asking_price,
            currency=payload.currency, status=payload.status, published_at=payload.published_at, notes=payload.notes)
        db.add(listing)
        db.flush()
        db.add(ListingPriceHistory(listing_id=listing.id, asking_price=listing.asking_price,
            currency=listing.currency, change_reason="created", recorded_by=current_user.id))
        db.commit()
        db.refresh(listing)
        return listing
    except Exception:
        db.rollback()
        raise


@router.post("", response_model=ListingRead, status_code=201)
def post_listing(payload: ListingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        payload = payload.model_copy(update={"created_by": current_user.id})
        return create_listing(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Kaynak ve harici ilan kimliği zaten kayıtlı veya ilişki kısıtı geçersiz.") from exc


@router.get("", response_model=list[ListingRead])
def list_listings(
    status: str | None = Query(default=None, pattern="^(active|passive|sold|withdrawn)$"),
    transaction_type: str | None = Query(default=None, pattern="^(sale|rent)$", description="Satış veya kiralama ilanları"),
    property_id: int | None = Query(default=None, gt=0),
    property_type: str | None = Query(default=None, min_length=1, max_length=40, description="Gayrimenkul türünün kodu; ör. apartment, villa, residential_land"),
    province_id: int | None = Query(default=None, gt=0),
    district_id: int | None = Query(default=None, gt=0),
    neighborhood_id: int | None = Query(default=None, gt=0),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_net_area_m2: float | None = Query(default=None, gt=0, description="Konut net alanı; arsa/tarla alanıyla karşılaştırılmaz."),
    max_net_area_m2: float | None = Query(default=None, gt=0),
    min_gross_area_m2: float | None = Query(default=None, gt=0, description="Konut brüt alanı; net alandan ayrıdır."),
    max_gross_area_m2: float | None = Query(default=None, gt=0),
    min_parcel_area_m2: float | None = Query(default=None, gt=0, description="İmar arsası veya tarla parsel alanı."),
    max_parcel_area_m2: float | None = Query(default=None, gt=0),
    min_room_count: int | None = Query(default=None, ge=1, le=30),
    max_room_count: int | None = Query(default=None, ge=1, le=30),
    min_building_age: int | None = Query(default=None, ge=0, le=300),
    max_building_age: int | None = Query(default=None, ge=0, le=300),
    zoning_status: str | None = Query(default=None, min_length=1, max_length=30),
    zoning_use: str | None = Query(default=None, min_length=1, max_length=40),
    source_name: str | None = Query(default=None, max_length=100),
    include_archived: bool = False,
    sort_by: str = Query(default="created_at", pattern="^(created_at|updated_at|asking_price|id)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Filter and page listings. Area filters are intentionally split by property type/measurement."""
    ranges = [
        ("min_price", min_price, "max_price", max_price),
        ("min_net_area_m2", min_net_area_m2, "max_net_area_m2", max_net_area_m2),
        ("min_gross_area_m2", min_gross_area_m2, "max_gross_area_m2", max_gross_area_m2),
        ("min_parcel_area_m2", min_parcel_area_m2, "max_parcel_area_m2", max_parcel_area_m2),
        ("min_room_count", min_room_count, "max_room_count", max_room_count),
        ("min_building_age", min_building_age, "max_building_age", max_building_age),
    ]
    for low_name, low, high_name, high in ranges:
        if low is not None and high is not None and low > high:
            raise HTTPException(status_code=422, detail=f"{low_name}, {high_name} değerinden büyük olamaz.")

    neighborhood = aliased(Location, name="neighborhood_filter")
    district = aliased(Location, name="district_filter")
    province = aliased(Location, name="province_filter")

    stmt = (
        select(Listing)
        .join(Property, Listing.property_id == Property.id)
        .join(PropertyType, Property.property_type_id == PropertyType.id)
        .outerjoin(ResidentialDetails, ResidentialDetails.property_id == Property.id)
        .outerjoin(LandDetails, LandDetails.property_id == Property.id)
        .outerjoin(FarmlandDetails, FarmlandDetails.property_id == Property.id)
        .outerjoin(neighborhood, and_(Property.location_id == neighborhood.id, neighborhood.level == "neighborhood"))
        .outerjoin(district, and_(
            district.level == "district",
            or_(Property.location_id == district.id, neighborhood.parent_id == district.id),
        ))
        .outerjoin(province, and_(
            province.level == "province",
            or_(Property.location_id == province.id, district.parent_id == province.id),
        ))
    )

    if not include_archived:
        stmt = stmt.where(Listing.archived_at.is_(None))
    if status is not None:
        stmt = stmt.where(Listing.status == status)
    if transaction_type is not None:
        stmt = stmt.where(Listing.transaction_type == transaction_type)
    if property_id is not None:
        stmt = stmt.where(Listing.property_id == property_id)
    if property_type is not None:
        stmt = stmt.where(PropertyType.code.in_(code_aliases(property_type)))
    if province_id is not None:
        stmt = stmt.where(province.id == province_id)
    if district_id is not None:
        stmt = stmt.where(district.id == district_id)
    if neighborhood_id is not None:
        stmt = stmt.where(neighborhood.id == neighborhood_id)
    if min_price is not None:
        stmt = stmt.where(Listing.asking_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.asking_price <= max_price)
    if min_net_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.net_area_m2 >= min_net_area_m2)
    if max_net_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.net_area_m2 <= max_net_area_m2)
    if min_gross_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.gross_area_m2 >= min_gross_area_m2)
    if max_gross_area_m2 is not None:
        stmt = stmt.where(ResidentialDetails.gross_area_m2 <= max_gross_area_m2)
    if min_parcel_area_m2 is not None or max_parcel_area_m2 is not None:
        land_area_conditions = []
        farmland_area_conditions = []
        if min_parcel_area_m2 is not None:
            land_area_conditions.append(LandDetails.parcel_area_m2 >= min_parcel_area_m2)
            farmland_area_conditions.append(FarmlandDetails.parcel_area_m2 >= min_parcel_area_m2)
        if max_parcel_area_m2 is not None:
            land_area_conditions.append(LandDetails.parcel_area_m2 <= max_parcel_area_m2)
            farmland_area_conditions.append(FarmlandDetails.parcel_area_m2 <= max_parcel_area_m2)
        stmt = stmt.where(or_(and_(*land_area_conditions), and_(*farmland_area_conditions)))
    if min_room_count is not None:
        stmt = stmt.where(ResidentialDetails.room_count >= min_room_count)
    if max_room_count is not None:
        stmt = stmt.where(ResidentialDetails.room_count <= max_room_count)
    if min_building_age is not None:
        stmt = stmt.where(ResidentialDetails.building_age >= min_building_age)
    if max_building_age is not None:
        stmt = stmt.where(ResidentialDetails.building_age <= max_building_age)
    if zoning_status is not None:
        stmt = stmt.where(LandDetails.zoning_status == zoning_status)
    if zoning_use is not None:
        stmt = stmt.where(LandDetails.zoning_use == zoning_use)
    if source_name is not None:
        stmt = stmt.where(Listing.source_name == source_name)

    sort_column = {
        "created_at": Listing.created_at,
        "updated_at": Listing.updated_at,
        "asking_price": Listing.asking_price,
        "id": Listing.id,
    }[sort_by]
    stmt = stmt.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc(), Listing.id.desc()).offset(offset).limit(limit)
    # Distinct prevents duplicates if legacy data contains multiple matching detail rows.
    return listing_summaries(db, list(db.scalars(stmt.distinct()).all()))


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise NotFoundError("İlan bulunamadı.")
    return listing_summaries(db, [listing])[0]


@router.patch("/{listing_id}", response_model=ListingRead)
def patch_listing(listing_id: int, payload: ListingUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise NotFoundError("İlan bulunamadı.")
    if current_user.role != "admin" and listing.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Yalnızca kendi ilanlarınızı güncelleyebilirsiniz.")
    try:
        return update_listing(db, listing_id, payload)
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("İlan güncellemesi veritabanı kısıtlarıyla çakışıyor.") from exc


@router.delete("/{listing_id}", status_code=204, response_class=Response)
def archive_listing(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise NotFoundError("İlan bulunamadı.")
    if current_user.role != "admin" and listing.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Yalnızca kendi ilanlarınızı arşivleyebilirsiniz.")
    if listing.archived_at is not None:
        return Response(status_code=204)
    listing.archived_at = datetime.now(timezone.utc)
    db.add(listing)
    db.commit()
    return Response(status_code=204)


@router.delete("/{listing_id}/permanent", status_code=204, response_class=Response)
def permanently_delete_listing(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    """Permanently delete a listing. Keep its property if it has other listings or recorded sales."""
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise NotFoundError("İlan bulunamadı.")
    if current_user.role != "admin" and listing.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Yalnızca kendi ilanlarınızı silebilirsiniz.")

    prop = db.get(Property, listing.property_id)
    other_listings = db.scalar(select(Listing.id).where(Listing.property_id == listing.property_id, Listing.id != listing.id).limit(1))
    has_sales = False
    if prop is not None:
        from app.models.sale_transaction import SaleTransaction
        has_sales = db.scalar(select(SaleTransaction.id).where(SaleTransaction.property_id == prop.id).limit(1)) is not None

    try:
        db.delete(listing)
        db.flush()
        if prop is not None and other_listings is None and not has_sales:
            db.delete(prop)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return Response(status_code=204)


@router.get("/{listing_id}/price-history", response_model=list[PriceHistoryRead])
def get_price_history(listing_id: int, db: Session = Depends(get_db)):
    if db.get(Listing, listing_id) is None:
        raise NotFoundError("İlan bulunamadı.")
    stmt = select(ListingPriceHistory).where(ListingPriceHistory.listing_id == listing_id).order_by(ListingPriceHistory.recorded_at, ListingPriceHistory.id)
    return list(db.scalars(stmt).all())
