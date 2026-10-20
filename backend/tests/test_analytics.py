from decimal import Decimal

from app.models.location import Location
from app.models.property import PropertyType, Property, ResidentialDetails, LandDetails, FarmlandDetails
from app.models.user import User


def _dataset(db):
    province = Location(level="province", name="İstanbul", normalized_name="istanbul")
    db.add(province); db.flush()
    district = Location(level="district", name="Kadıköy", normalized_name="kadikoy", parent_id=province.id)
    db.add(district); db.flush()
    neighborhood = Location(level="neighborhood", name="Moda", normalized_name="moda", parent_id=district.id)
    db.add(neighborhood)
    types = [
        PropertyType(id=1, code="apartment", name="Daire", group_code="residential"),
        PropertyType(id=2, code="residential_land", name="İmarlı Arsa", group_code="land"),
        PropertyType(id=3, code="farmland", name="Tarla", group_code="farmland"),
    ]
    user = User(email="analytics@example.com", username="analytics", password_hash="$argon2id$demo", full_name="Demo Agent", role="agent")
    db.add_all(types + [user]); db.flush()
    props = [Property(property_type_id=1, location_id=neighborhood.id) for _ in range(4)]
    land = Property(property_type_id=2, location_id=neighborhood.id)
    farmland = Property(property_type_id=3, location_id=neighborhood.id)
    db.add_all(props + [land, farmland]); db.flush()
    areas = [50, 100, 100, 50]
    for prop, area in zip(props, areas):
        db.add(ResidentialDetails(property_id=prop.id, net_area_m2=Decimal(area), gross_area_m2=Decimal(area + 20), room_count=3, building_age=8))
    db.add(LandDetails(property_id=land.id, parcel_area_m2=Decimal("500"), zoning_status="imarlı", zoning_use="konut"))
    db.add(FarmlandDetails(property_id=farmland.id, parcel_area_m2=Decimal("5000"), land_quality="good"))
    db.commit()
    return {"province": province, "district": district, "neighborhood": neighborhood, "user": user, "apartments": props, "land": land, "farmland": farmland}


def _listing(client, prop, user, price):
    r = client.post("/api/v1/listings", json={"property_id": prop.id, "created_by": user.id, "asking_price": str(price), "currency": "TRY"})
    assert r.status_code == 201, r.text
    return r.json()


def test_summary_has_correct_average_median_and_net_area_metrics(client, db_session):
    d = _dataset(db_session)
    prices = [10_000_000, 20_000_000, 30_000_000, 1_000_000_000]
    listings = [_listing(client, prop, d["user"], price) for prop, price in zip(d["apartments"], prices)]
    response = client.get("/api/v1/analytics/price-summary", params={"property_type": "apartment", "area_type": "net", "minimum_listings": 3})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["listing_count"] == 4
    assert Decimal(body["average_asking_price"]) == Decimal("265000000")
    assert Decimal(body["median_asking_price"]) == Decimal("25000000")
    assert Decimal(body["minimum_asking_price"]) == Decimal("10000000")
    assert Decimal(body["maximum_asking_price"]) == Decimal("1000000000")
    metric = body["area_price_metrics"][0]
    assert metric["area_type"] == "net"
    assert metric["listing_count"] == 4
    assert Decimal(metric["average_price_per_m2"]) == Decimal("5175000")
    assert Decimal(metric["median_price_per_m2"]) == Decimal("250000")
    assert body["reliability"] == "threshold_met"
    assert sum(bucket["count"] for bucket in body["price_distribution"]) == 4
    assert "gerçekleşmiş satış" in body["price_basis"]


def test_gross_area_changes_m2_metric_and_is_labelled(client, db_session):
    d = _dataset(db_session)
    _listing(client, d["apartments"][0], d["user"], 10_000_000)  # net 50, gross 70
    response = client.get("/api/v1/analytics/price-summary", params={"property_type": "apartment", "area_type": "gross"})
    assert response.status_code == 200
    metric = response.json()["area_price_metrics"][0]
    assert metric["area_type"] == "gross"
    assert Decimal(metric["average_price_per_m2"]) == Decimal("10000000") / Decimal("70")


def test_land_and_farmland_use_parcel_area_not_residential_area(client, db_session):
    d = _dataset(db_session)
    _listing(client, d["land"], d["user"], 5_000_000)
    _listing(client, d["farmland"], d["user"], 10_000_000)
    land = client.get("/api/v1/analytics/price-summary", params={"property_type": "residential_land"}).json()
    farm = client.get("/api/v1/analytics/price-summary", params={"property_type": "farmland"}).json()
    assert land["area_price_metrics"][0]["area_type"] == "parcel"
    assert Decimal(land["area_price_metrics"][0]["average_price_per_m2"]) == Decimal("10000")
    assert farm["area_price_metrics"][0]["area_type"] == "parcel"
    assert Decimal(farm["area_price_metrics"][0]["average_price_per_m2"]) == Decimal("2000")


def test_recorded_price_history_change_is_not_claimed_as_first_publish_price(client, db_session):
    d = _dataset(db_session)
    listing = _listing(client, d["apartments"][0], d["user"], 10_000_000)
    update = client.patch(f"/api/v1/listings/{listing['id']}", json={"asking_price": "12000000"})
    assert update.status_code == 200
    summary = client.get("/api/v1/analytics/price-summary", params={"property_type": "apartment"}).json()
    change = summary["observed_price_change"]
    assert change["listings_with_multiple_snapshots"] == 1
    assert Decimal(change["average_observed_change"]) == Decimal("2000000")
    assert Decimal(change["average_observed_change_percent"]) == Decimal("20")
    assert "ilk yayın fiyatı" in change["interpretation"]


def test_summary_reports_limited_reliability_when_sample_small(client, db_session):
    d = _dataset(db_session)
    _listing(client, d["apartments"][0], d["user"], 10_000_000)
    body = client.get("/api/v1/analytics/price-summary", params={"property_type": "apartment", "minimum_listings": 5}).json()
    assert body["listing_count"] == 1
    assert body["reliability"] == "limited"
    assert "istatistiksel güvence değildir" in body["reliability_note"]


def test_comparison_by_neighborhood_and_zoning_and_validates_type(client, db_session):
    d = _dataset(db_session)
    for prop, price in zip(d["apartments"][:2], [10_000_000, 20_000_000]):
        _listing(client, prop, d["user"], price)
    _listing(client, d["land"], d["user"], 5_000_000)
    neighborhood = client.get("/api/v1/analytics/compare", params={"property_type": "apartment", "group_by": "neighborhood"})
    assert neighborhood.status_code == 200, neighborhood.text
    assert neighborhood.json()["groups"][0]["listing_count"] == 2
    zoning = client.get("/api/v1/analytics/compare", params={"property_type": "residential_land", "group_by": "zoning_status"})
    assert zoning.status_code == 200
    assert zoning.json()["groups"][0]["group_label"] == "imarlı"
    rejected = client.get("/api/v1/analytics/compare", params={"group_by": "neighborhood"})
    assert rejected.status_code == 422


def test_analytics_filters_validate_negative_and_inverted_ranges(client):
    assert client.get("/api/v1/analytics/price-summary", params={"min_price": -1}).status_code == 422
    assert client.get("/api/v1/analytics/price-summary", params={"min_net_area_m2": -2}).status_code == 422
    assert client.get("/api/v1/analytics/price-summary", params={"min_price": 200, "max_price": 100}).status_code == 422
