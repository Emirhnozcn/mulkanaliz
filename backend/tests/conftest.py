import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.api.dependencies import get_current_user
from app.core.security import hash_password
from app.models.user import User
from app import models as _models  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        # Self-referencing location hierarchy requires FK checks disabled while SQLite drops tables.
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            Base.metadata.drop_all(connection)
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        engine.dispose()


@pytest.fixture()
def test_admin(db_session):
    user = User(
        email="test-admin@example.com",
        username="test-admin",
        password_hash=hash_password("Test-Admin-Passphrase-42!"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def client(db_session, test_admin):
    """Authenticated admin client for business-feature tests; auth is tested separately."""
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def anonymous_client(db_session):
    """Real authentication path with only the isolated test DB overridden."""
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
