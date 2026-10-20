from decimal import Decimal
from app.models.location import Location
from app.models.property import Property, PropertyType
from app.models.user import User


def seed_basics(db):
    location = Location(level="neighborhood", name="Merkez", normalized_name="merkez")
    ptype = PropertyType(id=1, code="apartment", name="Daire", group_code="residential")
    user = User(email="agent@example.com", username="agent", password_hash="$argon2id$placeholder-hash-value", full_name="Test Agent", role="agent")
    db.add_all([location, ptype, user])
    db.commit()
    prop = Property(property_type_id=ptype.id, location_id=location.id)
    db.add(prop)
    db.commit()
    return location, user, prop


def test_location_create_and_list(client):
    response = client.post("/api/v1/locations", json={"level":"province", "name":"İstanbul", "normalized_name":"istanbul"})
    assert response.status_code == 201, response.text
    location_id = response.json()["id"]
    listed = client.get("/api/v1/locations?level=province")
    assert listed.status_code == 200
    assert any(row["id"] == location_id for row in listed.json())


def test_user_create_and_list(client):
    response = client.post("/api/v1/users", json={"email":"AGENT@example.com", "username":"agent", "password":"Secure-Agent-Passphrase-42!", "full_name":"Test Agent", "role":"agent"})
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "agent@example.com"
    assert "password_hash" not in response.json()
    duplicate = client.post("/api/v1/users", json={"email":"agent@example.com", "username":"agent", "password":"Secure-Agent-Passphrase-42!", "full_name":"Duplicate", "role":"agent"})
    assert duplicate.status_code == 409


def test_listing_create_price_history_and_update(client, db_session):
    _, user, prop = seed_basics(db_session)
    payload = {"property_id":prop.id, "created_by":user.id, "asking_price":"4500000.00", "currency":"TRY", "source_type":"manual"}
    response = client.post("/api/v1/listings", json=payload)
    assert response.status_code == 201, response.text
    listing_id = response.json()["id"]
    history = client.get(f"/api/v1/listings/{listing_id}/price-history")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["change_reason"] == "created"

    update = client.patch(f"/api/v1/listings/{listing_id}", json={"asking_price":"4300000.00"})
    assert update.status_code == 200, update.text
    history = client.get(f"/api/v1/listings/{listing_id}/price-history")
    assert len(history.json()) == 2
    assert Decimal(history.json()[-1]["asking_price"]) == Decimal("4300000.00")

    no_price_change = client.patch(f"/api/v1/listings/{listing_id}", json={"notes":"updated notes"})
    assert no_price_change.status_code == 200
    history = client.get(f"/api/v1/listings/{listing_id}/price-history")
    assert len(history.json()) == 2


def test_duplicate_source_external_id_rejected(client, db_session):
    _, user, prop = seed_basics(db_session)
    payload = {"property_id":prop.id, "created_by":user.id, "asking_price":"1000000", "source_type":"import", "source_name":"authorized-feed", "source_listing_id":"abc-123"}
    first = client.post("/api/v1/listings", json=payload)
    assert first.status_code == 201, first.text
    second = client.post("/api/v1/listings", json=payload)
    assert second.status_code == 409, second.text
    assert len(client.get("/api/v1/listings").json()) == 1


def test_listing_invalid_foreign_key_returns_not_found(client):
    response = client.post("/api/v1/listings", json={"property_id":999, "created_by":999, "asking_price":"1000000"})
    assert response.status_code == 404


def test_invalid_price_rejected(client):
    response = client.post("/api/v1/listings", json={"property_id":1, "created_by":1, "asking_price":"-2"})
    assert response.status_code == 422


def test_listing_filter_by_transaction_type(client, db_session):
    _, user, prop = seed_basics(db_session)
    sale = client.post("/api/v1/listings", json={"property_id": prop.id, "asking_price": "4500000", "transaction_type": "sale"})
    rent = client.post("/api/v1/listings", json={"property_id": prop.id, "asking_price": "25000", "transaction_type": "rent"})
    assert sale.status_code == 201, sale.text
    assert rent.status_code == 201, rent.text
    sale_rows = client.get("/api/v1/listings", params={"transaction_type": "sale"})
    rent_rows = client.get("/api/v1/listings", params={"transaction_type": "rent"})
    assert sale_rows.status_code == 200 and len(sale_rows.json()) == 1
    assert rent_rows.status_code == 200 and len(rent_rows.json()) == 1
    assert sale_rows.json()[0]["transaction_type"] == "sale"
    assert rent_rows.json()[0]["transaction_type"] == "rent"


def test_listing_status_can_be_toggled_and_permanently_deleted(client, db_session):
    _, user, prop = seed_basics(db_session)
    created = client.post('/api/v1/listings', json={
        'property_id': prop.id, 'created_by': user.id, 'asking_price': '1250000',
        'currency': 'TRY', 'source_type': 'manual', 'status': 'active',
    })
    assert created.status_code == 201, created.text
    listing_id = created.json()['id']

    passive = client.patch(f'/api/v1/listings/{listing_id}', json={'status': 'passive'})
    assert passive.status_code == 200, passive.text
    assert passive.json()['status'] == 'passive'
    active = client.patch(f'/api/v1/listings/{listing_id}', json={'status': 'active'})
    assert active.status_code == 200, active.text
    assert active.json()['status'] == 'active'

    deleted = client.delete(f'/api/v1/listings/{listing_id}/permanent')
    assert deleted.status_code == 204, deleted.text
    assert client.get(f'/api/v1/listings/{listing_id}').status_code == 404
