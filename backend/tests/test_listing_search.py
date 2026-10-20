from decimal import Decimal

from app.models.location import Location
from app.models.property import FarmlandDetails, LandDetails, Property, PropertyType, ResidentialDetails
from app.models.user import User


def _seed_search_dataset(db):
    province = Location(level="province", name="İstanbul", normalized_name="istanbul")
    db.add(province)
    db.flush()
    district = Location(level="district", name="Kadıköy", normalized_name="kadikoy", parent_id=province.id)
    db.add(district)
    db.flush()
    neighborhood = Location(level="neighborhood", name="Moda", normalized_name="moda", parent_id=district.id)
    other_neighborhood = Location(level="neighborhood", name="Fenerbahçe", normalized_name="fenerbahce", parent_id=district.id)
    db.add_all([neighborhood, other_neighborhood])
    types = [
        PropertyType(id=1, code="apartment", name="Daire", group_code="residential"),
        PropertyType(id=2, code="residential_land", name="İmarlı Arsa", group_code="land"),
        PropertyType(id=3, code="farmland", name="Tarla", group_code="farmland"),
    ]
    user = User(email="search-agent@example.com", username="search-agent", password_hash="$argon2id$placeholder-hash-value", full_name="Search Agent", role="agent")
    db.add_all(types + [user])
    db.flush()

    apartment = Property(property_type_id=1, location_id=neighborhood.id)
    land = Property(property_type_id=2, location_id=neighborhood.id)
    farmland = Property(property_type_id=3, location_id=other_neighborhood.id)
    db.add_all([apartment, land, farmland])
    db.flush()
    db.add_all([
        ResidentialDetails(property_id=apartment.id, net_area_m2=Decimal("85"), gross_area_m2=Decimal("105"), room_count=3, building_age=10),
        LandDetails(property_id=land.id, parcel_area_m2=Decimal("400"), zoning_status="imarlı", zoning_use="konut"),
        FarmlandDetails(property_id=farmland.id, parcel_area_m2=Decimal("1200"), land_quality="good"),
    ])
    db.commit()
    return {"province": province, "district": district, "neighborhood": neighborhood, "other_neighborhood": other_neighborhood,
            "user": user, "apartment": apartment, "land": land, "farmland": farmland}


def _create_listing(client, prop, user, price, notes=None):
    response = client.post("/api/v1/listings", json={
        "property_id": prop.id,
        "created_by": user.id,
        "asking_price": str(price),
        "notes": notes,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_listing_filters_can_be_combined_and_location_hierarchy_works(client, db_session):
    data = _seed_search_dataset(db_session)
    apartment_listing = _create_listing(client, data["apartment"], data["user"], 5_000_000)
    detail = client.get(f"/api/v1/listings/{apartment_listing['id']}")
    assert detail.status_code == 200
    assert detail.json()["property_id"] == data["apartment"].id
    _create_listing(client, data["land"], data["user"], 3_000_000)
    _create_listing(client, data["farmland"], data["user"], 1_000_000)

    response = client.get("/api/v1/listings", params={
        "property_type": "apartment",
        "province_id": data["province"].id,
        "district_id": data["district"].id,
        "neighborhood_id": data["neighborhood"].id,
        "min_price": 4_000_000,
        "max_price": 6_000_000,
        "min_net_area_m2": 80,
        "max_net_area_m2": 90,
        "min_gross_area_m2": 100,
        "max_gross_area_m2": 110,
        "min_room_count": 3,
        "max_building_age": 15,
        "sort_by": "asking_price",
        "sort_order": "asc",
        "limit": 10,
        "offset": 0,
    })
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [apartment_listing["id"]]


def test_net_gross_area_filters_do_not_match_land_or_farmland(client, db_session):
    data = _seed_search_dataset(db_session)
    _create_listing(client, data["apartment"], data["user"], 5_000_000)
    _create_listing(client, data["land"], data["user"], 3_000_000)
    _create_listing(client, data["farmland"], data["user"], 1_000_000)

    response = client.get("/api/v1/listings", params={"min_net_area_m2": 50})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["property_id"] == data["apartment"].id


def test_parcel_area_and_zoning_filters_match_zoned_land_not_housing(client, db_session):
    data = _seed_search_dataset(db_session)
    _create_listing(client, data["apartment"], data["user"], 5_000_000)
    land_listing = _create_listing(client, data["land"], data["user"], 3_000_000)
    _create_listing(client, data["farmland"], data["user"], 1_000_000)

    response = client.get("/api/v1/listings", params={
        "min_parcel_area_m2": 350,
        "max_parcel_area_m2": 450,
        "zoning_status": "imarlı",
        "zoning_use": "konut",
    })
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [land_listing["id"]]


def test_price_sort_pagination_and_archive(client, db_session):
    data = _seed_search_dataset(db_session)
    first = _create_listing(client, data["apartment"], data["user"], 5_000_000)
    second = _create_listing(client, data["land"], data["user"], 2_000_000)

    page = client.get("/api/v1/listings", params={"sort_by": "asking_price", "sort_order": "asc", "limit": 1, "offset": 0})
    assert page.status_code == 200
    assert len(page.json()) == 1
    assert page.json()[0]["id"] == second["id"]

    archived = client.delete(f"/api/v1/listings/{second['id']}")
    assert archived.status_code == 204
    active_list = client.get("/api/v1/listings")
    assert [row["id"] for row in active_list.json()] == [first["id"]]
    all_list = client.get("/api/v1/listings", params={"include_archived": "true"})
    assert {row["id"] for row in all_list.json()} == {first["id"], second["id"]}
    assert client.delete(f"/api/v1/listings/{second['id']}").status_code == 204


def test_negative_and_inverted_filter_ranges_rejected(client):
    assert client.get("/api/v1/listings", params={"min_price": -1}).status_code == 422
    assert client.get("/api/v1/listings", params={"min_net_area_m2": -2}).status_code == 422
    assert client.get("/api/v1/listings", params={"min_price": 500, "max_price": 100}).status_code == 422
    assert client.get("/api/v1/listings", params={"sort_by": "asking_price desc; DROP TABLE listings"}).status_code == 422


def test_update_rejects_null_and_negative_price(client, db_session):
    data = _seed_search_dataset(db_session)
    listing = _create_listing(client, data["apartment"], data["user"], 5_000_000)
    assert client.patch(f"/api/v1/listings/{listing['id']}", json={"asking_price": None}).status_code == 422
    assert client.patch(f"/api/v1/listings/{listing['id']}", json={"asking_price": -10}).status_code == 422


def test_missing_listing_returns_404_on_detail_update_and_archive(client):
    assert client.get("/api/v1/listings/987654").status_code == 404
    assert client.patch("/api/v1/listings/987654", json={"notes": "x"}).status_code == 404
    assert client.delete("/api/v1/listings/987654").status_code == 404
