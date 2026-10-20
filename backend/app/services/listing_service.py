from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.core.errors import ConflictError, NotFoundError
from app.models.listing import Listing, ListingPriceHistory
from app.models.location import Location
from app.models.property import Property
from app.models.user import User
from app.schemas.listing import ListingCreate, ListingRead, ListingUpdate


def create_listing(db: Session, payload: ListingCreate) -> Listing:
    """Create listing and its initial price snapshot atomically."""
    data = payload.model_dump()
    if data.get("source_url") is not None:
        data["source_url"] = str(data["source_url"])
    try:
        with db.begin_nested():
            if db.get(Property, data["property_id"]) is None:
                raise NotFoundError("Gayrimenkul bulunamadı.")
            if db.get(User, data["created_by"]) is None:
                raise NotFoundError("İlanı oluşturan kullanıcı bulunamadı.")
            if data.get("source_listing_id") and not data.get("source_name"):
                raise ConflictError("Harici ilan kimliği kullanılıyorsa kaynak adı da zorunludur.")
            if data.get("source_name") and data.get("source_listing_id"):
                existing = db.scalar(select(Listing.id).where(
                    Listing.source_name == data["source_name"],
                    Listing.source_listing_id == data["source_listing_id"],
                ))
                if existing is not None:
                    raise ConflictError("Bu kaynakta aynı harici ilan kimliği zaten kayıtlı.")
            listing = Listing(**data)
            db.add(listing)
            db.flush()
            db.add(ListingPriceHistory(
                listing_id=listing.id,
                asking_price=listing.asking_price,
                currency=listing.currency,
                change_reason="created",
                recorded_by=listing.created_by,
            ))
        db.commit()
        db.refresh(listing)
        return listing
    except Exception:
        db.rollback()
        raise


def update_listing(db: Session, listing_id: int, payload: ListingUpdate) -> Listing:
    """Update listing and append a snapshot only when its asking price changes."""
    try:
        with db.begin_nested():
            listing = db.get(Listing, listing_id)
            if listing is None:
                raise NotFoundError("İlan bulunamadı.")
            updates = payload.model_dump(exclude_unset=True)
            if "property_id" in updates and updates["property_id"] is not None and db.get(Property, updates["property_id"]) is None:
                raise NotFoundError("Gayrimenkul bulunamadı.")
            old_price, old_currency = listing.asking_price, listing.currency
            for key, value in updates.items():
                if key == "source_url" and value is not None:
                    value = str(value)
                setattr(listing, key, value)
            price_changed = listing.asking_price != old_price or listing.currency != old_currency
            if price_changed:
                db.add(ListingPriceHistory(
                    listing=listing,
                    asking_price=listing.asking_price,
                    currency=listing.currency,
                    change_reason="price_changed",
                ))
            db.add(listing)
            db.flush()
        db.commit()
        db.refresh(listing)
        return listing
    except Exception:
        db.rollback()
        raise


def _strip_mah(name: str | None) -> str | None:
    return name.strip() if name else None


def _room_label(room_count: int | None, living_room_count: int | None) -> str | None:
    if not room_count:
        return None
    if living_room_count is not None and 0 <= living_room_count <= room_count:
        return f"{room_count - living_room_count}+{living_room_count}"
    return f"{room_count} oda"


def listing_summaries(db: Session, listings: list[Listing]) -> list[ListingRead]:
    """Attach distinguishing information (location, rooms, area...) to listings for list/detail views."""
    reads = [ListingRead.model_validate(item) for item in listings]
    if not reads:
        return reads
    property_ids = {item.property_id for item in reads}
    props = {
        p.id: p
        for p in db.scalars(
            select(Property).where(Property.id.in_(property_ids)).options(
                joinedload(Property.property_type),
                joinedload(Property.residential_details),
                joinedload(Property.land_details),
                joinedload(Property.farmland_details),
            )
        ).unique().all()
    }
    # Walk up the location tree (neighborhood -> district -> province) with a few batched queries.
    locations: dict[int, Location] = {}
    pending = {p.location_id for p in props.values()}
    while pending:
        rows = db.scalars(select(Location).where(Location.id.in_(pending))).all()
        for row in rows:
            locations[row.id] = row
        pending = {row.parent_id for row in rows if row.parent_id is not None and row.parent_id not in locations}

    for read in reads:
        prop = props.get(read.property_id)
        if prop is None:
            continue
        chain: dict[str, str] = {}
        node = locations.get(prop.location_id)
        while node is not None:
            chain[node.level] = node.name
            node = locations.get(node.parent_id) if node.parent_id is not None else None
        read.province_name = chain.get("province")
        read.district_name = chain.get("district")
        read.neighborhood_name = chain.get("neighborhood")
        read.location_label = " / ".join(
            part for part in (read.neighborhood_name, read.district_name, read.province_name) if part
        ) or None
        read.property_type_code = prop.property_type.code
        read.property_type_name = prop.property_type.name
        res, land, farm = prop.residential_details, prop.land_details, prop.farmland_details
        if res is not None:
            read.room_count = res.room_count
            read.living_room_count = res.living_room_count
            read.room_label = _room_label(res.room_count, res.living_room_count)
            read.net_area_m2 = res.net_area_m2
            read.gross_area_m2 = res.gross_area_m2
            read.building_age = res.building_age
            read.floor_number = res.floor_number
            read.total_floors = res.total_floors
        if land is not None:
            read.parcel_area_m2 = land.parcel_area_m2
        elif farm is not None:
            read.parcel_area_m2 = farm.parcel_area_m2
    return reads
