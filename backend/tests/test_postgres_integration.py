"""Opt-in PostgreSQL integration tests against a dedicated, disposable *_test database.

Run with TEST_POSTGRES_URL=postgresql+psycopg://.../rea_test pytest -q tests/test_postgres_integration.py
The database must be empty; this suite refuses URLs that do not clearly name a test database.
"""
import os
import subprocess
import sys
import uuid
from pathlib import Path
from sqlalchemy.engine import make_url

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models import Location, Listing, Property, PropertyType, User

BACKEND_DIR = Path(__file__).resolve().parents[1]


RESET_CONFIRMATION = "YES_RESET_DISPOSABLE_TEST_DATABASE"
LOCAL_TEST_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validate_test_database_target(database_url: str, configured_database_url: str | None) -> object:
    """Fail closed before connecting to a database that the fixture may reset/drop."""
    url = make_url(database_url)
    if url.drivername != "postgresql+psycopg":
        raise ValueError("TEST_POSTGRES_URL yalnızca postgresql+psycopg sürücüsünü kullanabilir.")
    if not url.database or not (url.database.endswith("_test") or url.database.endswith("_testing")):
        raise ValueError("Güvenlik için veritabanı adı _test veya _testing ile bitmeli.")
    if not url.host or url.host.lower() not in LOCAL_TEST_HOSTS:
        raise ValueError("Test veritabanı yalnızca localhost/loopback adresinde çalıştırılabilir.")
    if not url.username or "test" not in url.username.lower():
        raise ValueError("Test veritabanı kullanıcısının adında 'test' bulunmalıdır.")
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise ValueError("ENVIRONMENT=production iken PostgreSQL test/reset işlemi yasaktır.")
    if os.getenv("TEST_POSTGRES_RESET_CONFIRM") != RESET_CONFIRMATION:
        raise ValueError(
            "Test veritabanı sıfırlama onayı eksik. TEST_POSTGRES_RESET_CONFIRM="
            f"{RESET_CONFIRMATION} ayarlayın."
        )
    if url.query:
        raise ValueError("TEST_POSTGRES_URL query parametreleri kabul etmez; farklı schema/search_path yönlendirmesi yasaktır.")
    if configured_database_url:
        configured = make_url(configured_database_url)
        # Normalize loopback aliases so localhost and 127.0.0.1 cannot bypass target comparison.
        def normalized_host(host: str | None) -> str | None:
            if host and host.lower() in LOCAL_TEST_HOSTS:
                return "<loopback>"
            return host.lower() if host else None
        if (
            configured.database == url.database
            and normalized_host(configured.host) == normalized_host(url.host)
            and (configured.port or 5432) == (url.port or 5432)
        ):
            raise ValueError("TEST_POSTGRES_URL, DATABASE_URL ile aynı veritabanını hedefleyemez.")
    return url


@pytest.fixture(scope="session")
def postgres_engine():
    database_url = os.getenv("TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("TEST_POSTGRES_URL tanımlı değil; PostgreSQL entegrasyon testi çalıştırılmadı.")
    try:
        validate_test_database_target(database_url, os.getenv("DATABASE_URL"))
    except Exception as exc:
        # Configuration errors must fail before opening any database connection.
        pytest.fail(f"Güvenli PostgreSQL test hedefi doğrulanamadı: {exc}")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            server_version = int(connection.exec_driver_sql("SHOW server_version_num").scalar_one())
            actual_database = connection.exec_driver_sql("SELECT current_database()").scalar_one()
            actual_user = connection.exec_driver_sql("SELECT current_user").scalar_one()
        if server_version < 140000:
            engine.dispose()
            pytest.fail(f"PostgreSQL 14+ gerekli; bulunan server_version_num={server_version}.")
        if actual_database != make_url(database_url).database:
            engine.dispose()
            pytest.fail("Bağlanan PostgreSQL veritabanı URL'deki adla eşleşmiyor.")
        if actual_user != make_url(database_url).username:
            engine.dispose()
            pytest.fail("Bağlanan PostgreSQL rolü URL'deki test kullanıcısıyla eşleşmiyor.")
    except Exception as exc:
        engine.dispose()
        pytest.fail(f"PostgreSQL test sunucusu güvenli şekilde doğrulanamadı: {exc}")

    existing_tables = set(inspect(engine).get_table_names())
    if existing_tables:
        engine.dispose()
        pytest.fail(f"Temiz migration testi için boş bir test veritabanı gerekir; mevcut tablolar: {sorted(existing_tables)}")

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["ENVIRONMENT"] = "test"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR, env=env, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        # The target was validated as local, explicitly acknowledged, and initially empty.
        # Clean only this disposable test database so a retry starts from a known state.
        from app.db.base import Base
        from app import models as _models  # noqa: F401
        try:
            Base.metadata.drop_all(engine)
            with engine.begin() as connection:
                connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        finally:
            engine.dispose()
        pytest.fail(f"Alembic migration başarısız. stdout={result.stdout}\nstderr={result.stderr}")
    assert "users" in inspect(engine).get_table_names()
    assert "token_version" in {col["name"] for col in inspect(engine).get_columns("users")}
    with engine.connect() as connection:
        current_revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
    assert current_revision == "0002_token_version"

    yield engine

    # This URL is explicitly guarded as a disposable test database above.
    from app.db.base import Base
    from app import models as _models  # noqa: F401
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    engine.dispose()


@pytest.fixture()
def postgres_client(postgres_engine):
    factory = sessionmaker(bind=postgres_engine, class_=Session, autoflush=False, expire_on_commit=False)
    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _create_user(engine, role="agent"):
    email = f"pg-{uuid.uuid4().hex}@example.test"
    with Session(engine) as db:
        user = User(email=email, username=email.split("@")[0], full_name="Postgres Test", password_hash=hash_password("Postgres-Test-Passphrase-42!"), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, email


def _login(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "Postgres-Test-Passphrase-42!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_postgres_auth_rbac_listing_and_logout(postgres_engine, postgres_client):
    """Exercises real PostgreSQL constraints, transactions, login, ownership, and token revocation."""
    admin_id, admin_email = _create_user(postgres_engine, "admin")
    agent_id, agent_email = _create_user(postgres_engine, "agent")
    other_agent_id, other_agent_email = _create_user(postgres_engine, "agent")
    admin_headers = _login(postgres_client, admin_email)
    agent_headers = _login(postgres_client, agent_email)
    other_agent_headers = _login(postgres_client, other_agent_email)

    denied_users = postgres_client.get("/api/v1/users", headers=agent_headers)
    assert denied_users.status_code == 403
    admin_created_user = postgres_client.post("/api/v1/users", headers=admin_headers, json={
        "email": f"admin-created-{uuid.uuid4().hex}@example.test",
        "password": "A-Secure-Postgres-Passphrase-42!", "full_name": "Admin Created Agent", "role": "agent",
    })
    assert admin_created_user.status_code == 201, admin_created_user.text
    assert "password_hash" not in admin_created_user.json()

    location_response = postgres_client.post("/api/v1/locations", headers=admin_headers, json={
        "level": "neighborhood", "name": f"PG {uuid.uuid4().hex[:8]}", "normalized_name": f"pg-{uuid.uuid4().hex[:8]}"
    })
    assert location_response.status_code == 201, location_response.text
    location_id = location_response.json()["id"]

    with Session(postgres_engine) as db:
        property_type = db.scalar(select(PropertyType).where(PropertyType.code == "apartment"))
        prop = Property(property_type_id=property_type.id, location_id=location_id)
        db.add(prop)
        db.commit()
        db.refresh(prop)
        property_id = prop.id

    created = postgres_client.post("/api/v1/listings", headers=agent_headers, json={
        "property_id": property_id, "created_by": admin_id, "asking_price": "1250000.00"
    })
    assert created.status_code == 201, created.text
    assert created.json()["created_by"] == agent_id
    listing_id = created.json()["id"]
    detail = postgres_client.get(f"/api/v1/listings/{listing_id}", headers=agent_headers)
    assert detail.status_code == 200, detail.text

    foreign_update = postgres_client.patch(f"/api/v1/listings/{listing_id}", headers=other_agent_headers, json={"asking_price": "1"})
    foreign_archive = postgres_client.delete(f"/api/v1/listings/{listing_id}", headers=other_agent_headers)
    assert foreign_update.status_code == 403
    assert foreign_archive.status_code == 403

    updated = postgres_client.patch(f"/api/v1/listings/{listing_id}", headers=agent_headers, json={"asking_price": "1300000.00"})
    assert updated.status_code == 200, updated.text
    history = postgres_client.get(f"/api/v1/listings/{listing_id}/price-history", headers=agent_headers)
    assert history.status_code == 200, history.text
    assert len(history.json()) >= 2
    archived = postgres_client.delete(f"/api/v1/listings/{listing_id}", headers=agent_headers)
    assert archived.status_code == 204

    import_payload = {
        "source_url": f"https://example.org/ilan/{uuid.uuid4().hex}",
        "source_name": "example.org", "source_listing_id": f"pg-{uuid.uuid4().hex}",
        "location_id": location_id, "property_type_code": "apartment",
        "asking_price": "2400000.00", "net_area_m2": "80", "gross_area_m2": "100",
    }
    imported = postgres_client.post("/api/v1/imports/listing", headers=agent_headers, json=import_payload)
    assert imported.status_code == 201, imported.text
    import_payload["asking_price"] = "2200000.00"
    foreign_reimport = postgres_client.post("/api/v1/imports/listing", headers=other_agent_headers, json=import_payload)
    assert foreign_reimport.status_code == 403
    with Session(postgres_engine) as db:
        imported_listing = db.get(Listing, imported.json()["listing_id"])
        assert str(imported_listing.asking_price) == "2400000.00"
        from sqlalchemy.exc import IntegrityError
        duplicate = Listing(
            property_id=imported_listing.property_id, created_by=agent_id,
            source_type="authorized_source", source_name=imported_listing.source_name,
            source_listing_id=imported_listing.source_listing_id,
            source_url=f"https://example.org/duplicate/{uuid.uuid4().hex}",
            asking_price=imported_listing.asking_price, currency=imported_listing.currency,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        duplicate_count = db.query(Listing).filter(
            Listing.source_name == imported_listing.source_name,
            Listing.source_listing_id == imported_listing.source_listing_id,
        ).count()
        assert duplicate_count == 1

    logout = postgres_client.post("/api/v1/auth/logout", headers=agent_headers)
    assert logout.status_code == 204
    assert postgres_client.get("/api/v1/auth/me", headers=agent_headers).status_code == 401


def test_postgres_import_is_idempotent_and_constraints_hold(postgres_engine, postgres_client):
    """Checks source uniqueness, price-history writes and DB constraints on PostgreSQL."""
    agent_id, email = _create_user(postgres_engine, "agent")
    headers = _login(postgres_client, email)
    location = postgres_client.post("/api/v1/locations", headers=_login(postgres_client, _create_user(postgres_engine, "admin")[1]), json={
        "level": "province", "name": f"PG Province {uuid.uuid4().hex[:8]}",
        "normalized_name": f"pg-province-{uuid.uuid4().hex[:8]}"
    })
    assert location.status_code == 201, location.text
    payload = {
        "source_url": f"https://example.org/ilan/{uuid.uuid4().hex}",
        "source_name": "example.org", "source_listing_id": f"pg-id-{uuid.uuid4().hex}",
        "location_id": location.json()["id"], "property_type_code": "apartment",
        "asking_price": "1800000.00", "net_area_m2": "75", "gross_area_m2": "90",
    }
    first = postgres_client.post("/api/v1/imports/listing", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    history_before = postgres_client.get(f"/api/v1/listings/{first.json()['listing_id']}/price-history", headers=headers)
    assert history_before.status_code == 200, history_before.text
    assert len(history_before.json()) == 1

    same = postgres_client.post("/api/v1/imports/listing", headers=headers, json=payload)
    assert same.status_code == 200, same.text
    assert same.json()["action"] == "unchanged"
    history_same = postgres_client.get(f"/api/v1/listings/{first.json()['listing_id']}/price-history", headers=headers)
    assert len(history_same.json()) == 1

    payload["asking_price"] = "1750000.00"
    changed = postgres_client.post("/api/v1/imports/listing", headers=headers, json=payload)
    assert changed.status_code == 200, changed.text
    assert changed.json()["action"] == "updated"
    history_changed = postgres_client.get(f"/api/v1/listings/{first.json()['listing_id']}/price-history", headers=headers)
    assert len(history_changed.json()) == 2

    from sqlalchemy.exc import IntegrityError
    with Session(postgres_engine) as db:
        # PostgreSQL CHECK constraint must reject a negative asking price even if API validation is bypassed.
        listing = db.scalar(select(Listing).where(Listing.id == first.json()["listing_id"]))
        listing.asking_price = -1
        db.add(listing)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        listing = db.get(Listing, first.json()["listing_id"])
        assert listing is not None
        assert str(listing.asking_price) == "1750000.00"


def _safety_test_url(database="rea_test", host="127.0.0.1", user="rea_test_user", port=55432):
    return f"postgresql+psycopg://{user}:not-a-real-secret@{host}:{port}/{database}"


def test_postgres_target_requires_explicit_reset_acknowledgement(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("TEST_POSTGRES_RESET_CONFIRM", raising=False)
    with pytest.raises(ValueError, match="sıfırlama onayı eksik"):
        validate_test_database_target(_safety_test_url(), "sqlite+pysqlite:///:memory:")


def test_postgres_target_rejects_remote_host(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TEST_POSTGRES_RESET_CONFIRM", RESET_CONFIRMATION)
    with pytest.raises(ValueError, match="localhost/loopback"):
        validate_test_database_target(_safety_test_url(host="db.production.example"), None)


def test_postgres_target_rejects_non_test_database_name(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TEST_POSTGRES_RESET_CONFIRM", RESET_CONFIRMATION)
    with pytest.raises(ValueError, match="_test veya _testing"):
        validate_test_database_target(_safety_test_url(database="real_estate_analytics"), None)


def test_postgres_target_rejects_same_target_as_configured_database(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TEST_POSTGRES_RESET_CONFIRM", RESET_CONFIRMATION)
    configured_url = _safety_test_url(host="localhost", user="production_app")
    with pytest.raises(ValueError, match="aynı veritabanını hedefleyemez"):
        validate_test_database_target(_safety_test_url(host="127.0.0.1"), configured_url)


def test_postgres_target_rejects_production_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TEST_POSTGRES_RESET_CONFIRM", RESET_CONFIRMATION)
    with pytest.raises(ValueError, match="production"):
        validate_test_database_target(_safety_test_url(), None)


def test_postgres_target_rejects_url_query_parameters(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TEST_POSTGRES_RESET_CONFIRM", RESET_CONFIRMATION)
    with pytest.raises(ValueError, match="query parametreleri kabul etmez"):
        validate_test_database_target(_safety_test_url() + "?options=-csearch_path%3Dpublic", None)
