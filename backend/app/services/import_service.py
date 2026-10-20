from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.errors import ConflictError, NotFoundError
from app.models.listing import Listing, ListingPriceHistory
from app.models.location import Location
from app.models.property import FarmlandDetails, LandDetails, Property, PropertyType, ResidentialDetails
from app.models.user import User
from app.schemas.import_listing import ImportListingRequest


def import_listing(db: Session, payload: ImportListingRequest, actor: User | None = None) -> dict:
    """Idempotently import one user-confirmed listing and track only observed price changes."""
    data = payload.model_dump()
    data["source_url"] = str(data["source_url"])
    try:
        with db.begin_nested():
            user = db.get(User, data["created_by"])
            if user is None or not user.is_active:
                raise NotFoundError("Aktif danışman bulunamadı.")
            location = db.get(Location, data["location_id"])
            if location is None:
                raise NotFoundError("Seçilen konum bulunamadı.")
            prop_type = db.scalar(select(PropertyType).where(
                PropertyType.code == data["property_type_code"], PropertyType.is_active.is_(True)
            ))
            if prop_type is None:
                raise NotFoundError("Gayrimenkul türü bulunamadı; tür kodları seed edilmelidir.")

            existing = None
            if data.get("source_listing_id"):
                existing = db.scalar(select(Listing).where(
                    Listing.source_name == data["source_name"],
                    Listing.source_listing_id == data["source_listing_id"],
                ))
            if existing is None:
                # URLs are a useful fallback identity when a provider exposes no stable listing ID.
                existing = db.scalar(select(Listing).where(
                    Listing.source_name == data["source_name"], Listing.source_url == data["source_url"]
                ))

            if existing is not None:
                if actor is not None and actor.role != "admin" and existing.created_by != actor.id:
                    raise HTTPException(status_code=403, detail="Bu kaynak ilan başka bir danışmana ait; güncelleme yetkiniz yok.")
                prop = db.get(Property, existing.property_id)
                if prop is None:
                    raise ConflictError("Mevcut ilan kaydı geçersiz bir gayrimenkule bağlı.")
                if prop.property_type_id != prop_type.id:
                    raise ConflictError("Bu kaynak ilanı farklı tür ile kayıtlı. Önce kaydı elle kontrol edin.")
                if prop.location_id != data["location_id"]:
                    # Kullanıcı önizlemede konumu onayladı; daha önce eksik/yanlış okunmuş konumu düzelt.
                    prop.location_id = data["location_id"]
                price_changed = existing.asking_price != data["asking_price"] or existing.currency != data["currency"] or existing.transaction_type != data.get("transaction_type", "sale")
                existing.transaction_type = data.get("transaction_type", "sale")
                existing.asking_price = data["asking_price"]
                existing.currency = data["currency"]
                existing.source_url = data["source_url"]
                existing.last_seen_at = datetime.now(timezone.utc)
                existing.published_at = existing.published_at or data.get("published_at")
                # Only replace descriptive notes when new non-empty user-confirmed information exists.
                if data.get("notes") or data.get("title"):
                    existing.notes = data.get("notes") or data.get("title")
                if data.get("title"):
                    existing.title = data["title"]
                if data.get("address"):
                    prop.address = data["address"]
                if data.get("title"):
                    prop.notes = data["title"]
                if prop_type.group_code == "residential":
                    details = db.get(ResidentialDetails, prop.id)
                    if details is None:
                        details = ResidentialDetails(property_id=prop.id)
                        db.add(details)
                    for field in ("net_area_m2", "gross_area_m2", "room_count", "living_room_count", "building_age", "floor_number", "total_floors"):
                        if data.get(field) is not None:
                            setattr(details, field, data[field])
                elif data["property_type_code"] == "farmland":
                    details = db.get(FarmlandDetails, prop.id)
                    if details is None:
                        details = FarmlandDetails(property_id=prop.id, parcel_area_m2=data["parcel_area_m2"])
                        db.add(details)
                    if data.get("parcel_area_m2") is not None:
                        details.parcel_area_m2 = data["parcel_area_m2"]
                        prop.land_area_m2 = data["parcel_area_m2"]
                else:
                    details = db.get(LandDetails, prop.id)
                    if details is None:
                        details = LandDetails(property_id=prop.id, parcel_area_m2=data["parcel_area_m2"])
                        db.add(details)
                    if data.get("parcel_area_m2") is not None:
                        details.parcel_area_m2 = data["parcel_area_m2"]
                        prop.land_area_m2 = data["parcel_area_m2"]
                    if data.get("zoning_status") is not None:
                        details.zoning_status = data["zoning_status"]
                    if data.get("zoning_use") is not None:
                        details.zoning_use = data["zoning_use"]
                db.add(prop)
                db.add(existing)
                db.flush()
                if price_changed:
                    db.add(ListingPriceHistory(
                        listing_id=existing.id, asking_price=existing.asking_price,
                        currency=existing.currency, change_reason="price_changed", recorded_by=data["created_by"],
                    ))
                # Keep the current observation even when price did not change; price history is for changes.
                action = "updated" if price_changed else "unchanged"
                listing_id, property_id = existing.id, existing.property_id
            else:
                prop = Property(
                    property_type_id=prop_type.id,
                    location_id=location.id,
                    address=data.get("address"),
                    notes=data.get("title"),
                    land_area_m2=data.get("parcel_area_m2"),
                )
                db.add(prop)
                db.flush()
                if prop_type.group_code == "residential":
                    db.add(ResidentialDetails(
                        property_id=prop.id, net_area_m2=data.get("net_area_m2"),
                        gross_area_m2=data.get("gross_area_m2"), room_count=data.get("room_count"),
                        living_room_count=data.get("living_room_count"),
                        building_age=data.get("building_age"), floor_number=data.get("floor_number"),
                        total_floors=data.get("total_floors"),
                    ))
                elif data["property_type_code"] == "farmland":
                    db.add(FarmlandDetails(property_id=prop.id, parcel_area_m2=data["parcel_area_m2"]))
                else:
                    db.add(LandDetails(
                        property_id=prop.id, parcel_area_m2=data["parcel_area_m2"],
                        zoning_status=data.get("zoning_status"), zoning_use=data.get("zoning_use"),
                    ))
                listing = Listing(
                    property_id=prop.id, created_by=data["created_by"], source_type="authorized_source",
                    source_name=data["source_name"], source_listing_id=data.get("source_listing_id"),
                    source_url=data["source_url"], title=data.get("title"), transaction_type=data.get("transaction_type", "sale"), asking_price=data["asking_price"], currency=data["currency"],
                    status="active", published_at=data.get("published_at"), last_seen_at=datetime.now(timezone.utc),
                    notes=data.get("notes") or data.get("title"),
                )
                db.add(listing)
                db.flush()
                db.add(ListingPriceHistory(
                    listing_id=listing.id, asking_price=listing.asking_price, currency=listing.currency,
                    change_reason="created", recorded_by=data["created_by"],
                ))
                listing_id, property_id = listing.id, prop.id
                action, price_changed = "created", False
        db.commit()
        return {
            "listing_id": listing_id, "property_id": property_id, "action": action,
            "price_changed": price_changed,
            "message": {
                "created": "İlan aktarıldı.",
                "updated": "İlanın gözlenen fiyatı güncellendi ve fiyat geçmişine eklendi.",
                "unchanged": "İlan zaten kayıtlı; fiyat değişmediği için yeni fiyat geçmişi kaydı eklenmedi.",
            }[action],
        }
    except Exception:
        db.rollback()
        raise
