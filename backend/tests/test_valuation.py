from decimal import Decimal

from app.models.listing import Listing
from app.models.location import Location
from app.models.property import FarmlandDetails, LandDetails, Property, PropertyType, ResidentialDetails
from app.models.user import User


def _seed(db):
    province = Location(level="province", name="Bolu", normalized_name="bolu"); db.add(province); db.flush()
    district = Location(level="district", name="Merkez", normalized_name="merkez", parent_id=province.id); db.add(district); db.flush()
    hood = Location(level="neighborhood", name="Gölyüzü", normalized_name="gölyüzü", parent_id=district.id)
    other = Location(level="neighborhood", name="Ihsaniye", normalized_name="ihsaniye", parent_id=district.id)
    db.add_all([hood, other])
    db.add_all([
        PropertyType(id=1, code="apartment", name="Daire", group_code="residential"),
        PropertyType(id=4, code="residential_zoned_land", name="Konut İmarlı Arsa", group_code="land"),
        PropertyType(id=6, code="farmland", name="Tarla", group_code="farmland"),
    ])
    user = User(email="v@example.com", username="v", password_hash="x", full_name="V", role="agent")
    db.add(user); db.commit()
    return province, district, hood, other, user


def _apartment(db, hood, user, price, net, rooms=3, tx="sale"):
    prop = Property(property_type_id=1, location_id=hood.id); db.add(prop); db.flush()
    db.add(ResidentialDetails(property_id=prop.id, net_area_m2=Decimal(net), room_count=rooms))
    db.add(Listing(property_id=prop.id, created_by=user.id, source_type="manual", transaction_type=tx, asking_price=Decimal(price), currency="TRY", status="active"))
    db.commit()


def _land(db, hood, user, price, area, type_id=4):
    prop = Property(property_type_id=type_id, location_id=hood.id); db.add(prop); db.flush()
    model = LandDetails if type_id == 4 else FarmlandDetails
    db.add(model(property_id=prop.id, parcel_area_m2=Decimal(area)))
    db.add(Listing(property_id=prop.id, created_by=user.id, source_type="manual", transaction_type="sale", asking_price=Decimal(price), currency="TRY", status="active"))
    db.commit()


def _params(province, district, hood, **extra):
    return {"province_id": province.id, "district_id": district.id, "neighborhood_id": hood.id, **extra}


def test_apartment_valuation_uses_neighborhood_median_and_total_room_count(client, db_session):
    province, district, hood, other, user = _seed(db_session)
    for price, net in [(2_000_000, 100), (2_200_000, 100), (1_800_000, 90), (2_400_000, 110)]:
        _apartment(db_session, hood, user, price, net, rooms=3)
    _apartment(db_session, hood, user, 9_000_000, 100, rooms=5)  # farklı oda: eşleşmemeli
    r = client.get("/api/v1/analytics/valuation", params=_params(province, district, hood, property_type="apartment", area_m2=100, room_count=3))
    assert r.status_code == 200, r.text
    sale = r.json()["sale_estimate"]
    assert sale["comparable_count"] == 4
    assert sale["source_level"] == "neighborhood"
    assert 1_900_000 < sale["estimated_price"] < 2_300_000
    assert r.json()["rent_estimate"]["estimated_price"] is None


def test_valuation_falls_back_to_district_when_neighborhood_has_too_few(client, db_session):
    province, district, hood, other, user = _seed(db_session)
    _apartment(db_session, hood, user, 2_000_000, 100)
    for price in (2_100_000, 2_200_000, 1_900_000):
        _apartment(db_session, other, user, price, 100)
    sale = client.get("/api/v1/analytics/valuation", params=_params(province, district, hood, property_type="apartment", area_m2=100)).json()["sale_estimate"]
    assert sale["comparable_count"] == 4 and sale["source_level"] == "district"


def test_valuation_uses_single_comparable_instead_of_failing(client, db_session):
    province, district, hood, other, user = _seed(db_session)
    _apartment(db_session, hood, user, 2_000_000, 100)
    sale = client.get("/api/v1/analytics/valuation", params=_params(province, district, hood, property_type="apartment", area_m2=100)).json()["sale_estimate"]
    assert sale["comparable_count"] == 1 and sale["reliability"] == "limited" and sale["estimated_price"] == 2_000_000


def test_land_valuation_works_with_zoned_land_code_and_alias(client, db_session):
    province, district, hood, other, user = _seed(db_session)
    for price, area in [(6_900_000, 1000), (3_500_000, 500), (7_200_000, 1000), (1_400_000, 200)]:
        _land(db_session, hood, user, price, area)
    for code in ("residential_zoned_land", "residential_land"):
        r = client.get("/api/v1/analytics/valuation", params=_params(province, district, hood, property_type=code, area_m2=800, area_type="parcel"))
        assert r.status_code == 200, r.text
        sale = r.json()["sale_estimate"]
        assert sale["comparable_count"] >= 3 and 5_000_000 < sale["estimated_price"] < 6_500_000


def test_farmland_valuation(client, db_session):
    province, district, hood, other, user = _seed(db_session)
    for price, area in [(500_000, 5000), (520_000, 5200), (480_000, 4800)]:
        _land(db_session, hood, user, price, area, type_id=6)
    sale = client.get("/api/v1/analytics/valuation", params=_params(province, district, hood, property_type="farmland", area_m2=5000, area_type="parcel")).json()["sale_estimate"]
    assert sale["comparable_count"] == 3 and 450_000 < sale["estimated_price"] < 550_000


def test_obvious_price_typos_are_trimmed_from_comparables(client, db_session):
    province, district, hood, other, user = _seed(db_session)
    for price, area in [(6_900_000, 1000), (7_000_000, 1000), (7_100_000, 1000), (7, 1000)]:  # 7 TL = hatalı okunmuş fiyat
        _land(db_session, hood, user, price, area)
    sale = client.get("/api/v1/analytics/valuation", params=_params(province, district, hood, property_type="residential_zoned_land", area_m2=1000, area_type="parcel")).json()["sale_estimate"]
    assert sale["comparable_count"] == 3 and sale["estimated_price"] == 7_000_000


def test_land_type_aliases_work_in_listing_and_analytics_filters(client, db_session):
    province, district, hood, other, user = _seed(db_session)
    _land(db_session, hood, user, 6_900_000, 1000)
    for code in ("residential_zoned_land", "residential_land"):
        assert len(client.get("/api/v1/listings", params={"property_type": code}).json()) == 1
        summary = client.get("/api/v1/analytics/price-summary", params={"property_type": code})
        assert summary.status_code == 200 and summary.json()["listing_count"] == 1
