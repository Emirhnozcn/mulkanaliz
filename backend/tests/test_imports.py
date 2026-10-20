from decimal import Decimal
import pytest
from app.models.listing import Listing, ListingPriceHistory
from app.models.location import Location
from app.models.property import FarmlandDetails, Property, PropertyType, ResidentialDetails
from app.models.user import User


def seed_import_basics(db):
    location = Location(level="neighborhood", name="Moda", normalized_name="moda")
    apartment_type = PropertyType(id=1, code="apartment", name="Daire", group_code="residential")
    farmland_type = PropertyType(id=2, code="farmland", name="Tarla", group_code="farmland")
    land_type = PropertyType(id=3, code="residential_zoned_land", name="İmarlı Arsa", group_code="land")
    user = User(email="import-agent@example.com", username="import-agent", password_hash="hash-placeholder", full_name="Import Agent", role="agent")
    db.add_all([location, apartment_type, farmland_type, land_type, user])
    db.commit()
    return location, user


def apartment_payload(location, user, **overrides):
    data = {
        "source_url": "https://example.org/ilan/123456", "source_name": "example.org",
        "source_listing_id": "123456", "created_by": user.id, "location_id": location.id,
        "property_type_code": "apartment", "asking_price": "4250000", "currency": "TRY",
        "title": "Moda'da daire", "net_area_m2": "85", "gross_area_m2": "105", "room_count": 3,
    }
    data.update(overrides)
    return data


def test_import_creates_property_listing_and_initial_price_history(client, db_session):
    location, user = seed_import_basics(db_session)
    response = client.post("/api/v1/imports/listing", json=apartment_payload(location, user))
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["action"] == "created"
    prop = db_session.get(Property, result["property_id"])
    details = db_session.get(ResidentialDetails, prop.id)
    assert details.net_area_m2 == Decimal("85.00")
    assert details.gross_area_m2 == Decimal("105.00")
    history = db_session.query(ListingPriceHistory).filter_by(listing_id=result["listing_id"]).all()
    assert len(history) == 1
    assert history[0].change_reason == "created"


def test_reimport_same_listing_is_idempotent_and_price_change_appends_history(client, db_session):
    location, user = seed_import_basics(db_session)
    first = client.post("/api/v1/imports/listing", json=apartment_payload(location, user))
    assert first.status_code == 201, first.text
    second = client.post("/api/v1/imports/listing", json=apartment_payload(location, user))
    assert second.status_code == 200, second.text
    assert second.json()["action"] == "unchanged"
    assert db_session.query(Listing).count() == 1
    assert db_session.query(Property).count() == 1
    assert db_session.query(ListingPriceHistory).count() == 1

    changed = client.post("/api/v1/imports/listing", json=apartment_payload(location, user, asking_price="4100000"))
    assert changed.status_code == 200, changed.text
    assert changed.json()["action"] == "updated"
    assert changed.json()["price_changed"] is True
    history = db_session.query(ListingPriceHistory).order_by(ListingPriceHistory.id).all()
    assert len(history) == 2
    assert history[-1].asking_price == Decimal("4100000.00")
    assert history[-1].change_reason == "price_changed"


def test_import_requires_parcel_area_for_land_and_rejects_residential_fields(client, db_session):
    location, user = seed_import_basics(db_session)
    missing_parcel = {
        "source_url": "https://example.org/ilan/777777", "source_name": "example.org",
        "created_by": user.id, "location_id": location.id, "property_type_code": "farmland", "asking_price": "1000000",
    }
    response = client.post("/api/v1/imports/listing", json=missing_parcel)
    assert response.status_code == 422
    mixed = apartment_payload(location, user, property_type_code="farmland", net_area_m2="85", parcel_area_m2="1200")
    response = client.post("/api/v1/imports/listing", json=mixed)
    assert response.status_code == 422


def test_import_unknown_source_or_location_returns_404(client, db_session):
    location, user = seed_import_basics(db_session)
    response = client.post("/api/v1/imports/listing", json=apartment_payload(location, user, location_id=999))
    assert response.status_code == 404
    # Client-supplied created_by is ignored; the authenticated principal owns the new record.
    response = client.post("/api/v1/imports/listing", json=apartment_payload(location, user, created_by=999, source_listing_id="different-id", source_url="https://example.org/ilan/999999"))
    assert response.status_code == 201, response.text


def test_reimport_without_external_id_uses_source_url_as_fallback(client, db_session):
    location, user = seed_import_basics(db_session)
    payload = apartment_payload(location, user, source_listing_id=None)
    first = client.post("/api/v1/imports/listing", json=payload)
    second = client.post("/api/v1/imports/listing", json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["action"] == "unchanged"
    assert db_session.query(Listing).count() == 1


def test_farmland_import_keeps_parcel_area_separate(client, db_session):
    location, user = seed_import_basics(db_session)
    payload = {
        "source_url": "https://example.org/ilan/tarla-777777", "source_name": "example.org",
        "source_listing_id": "tarla-777777", "created_by": user.id, "location_id": location.id,
        "property_type_code": "farmland", "asking_price": "1900000", "parcel_area_m2": "2500",
    }
    response = client.post("/api/v1/imports/listing", json=payload)
    assert response.status_code == 201, response.text
    prop = db_session.get(Property, response.json()["property_id"])
    assert prop.land_area_m2 == Decimal("2500.00")
    assert db_session.get(FarmlandDetails, prop.id).parcel_area_m2 == Decimal("2500.00")
    assert db_session.get(ResidentialDetails, prop.id) is None


def test_listing_list_and_detail_expose_distinguishing_summary(client, db_session):
    province = Location(level="province", name="Bolu", normalized_name="bolu")
    db_session.add(province); db_session.commit()
    district = Location(level="district", name="Merkez", normalized_name="merkez", parent_id=province.id)
    db_session.add(district); db_session.commit()
    hood = Location(level="neighborhood", name="Gölyüzü", normalized_name="gölyüzü", parent_id=district.id)
    db_session.add(hood)
    db_session.add(PropertyType(id=1, code="apartment", name="Daire", group_code="residential"))
    user = User(email="a@example.com", username="a", password_hash="x", full_name="A", role="agent")
    db_session.add(user); db_session.commit()
    resp = client.post("/api/v1/imports/listing", json=apartment_payload(hood, user, room_count=3, living_room_count=1, building_age=5, floor_number=2, total_floors=6))
    assert resp.status_code == 201, resp.text
    rows = client.get("/api/v1/listings").json()
    assert rows[0]["location_label"] == "Gölyüzü / Merkez / Bolu"
    assert rows[0]["neighborhood_name"] == "Gölyüzü"
    assert rows[0]["room_label"] == "2+1"
    assert rows[0]["property_type_name"] == "Daire"
    detail = client.get(f"/api/v1/listings/{rows[0]['id']}").json()
    assert detail["province_name"] == "Bolu" and detail["floor_number"] == 2 and detail["total_floors"] == 6


def test_reimport_with_corrected_location_updates_property_location(client, db_session):
    location, user = seed_import_basics(db_session)
    other = Location(level="neighborhood", name="Kadıköy", normalized_name="kadıköy")
    db_session.add(other); db_session.commit()
    assert client.post("/api/v1/imports/listing", json=apartment_payload(location, user)).status_code == 201
    again = client.post("/api/v1/imports/listing", json=apartment_payload(other, user))
    assert again.status_code == 200, again.text
    assert db_session.query(Property).one().location_id == other.id
