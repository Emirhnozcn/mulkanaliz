
import pytest
from pathlib import Path
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.core.config import Settings


def test_production_rejects_development_secrets_and_local_defaults():
    with pytest.raises(ValidationError):
        Settings(environment="production")


def test_production_accepts_explicit_secure_configuration():
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://rea_user:replace-me@db.example.com:5432/rea",
        jwt_secret_key="K" * 48,
        cors_origins="https://app.example.com",
        allowed_hosts="api.example.com",
        secure_cookies=True,
        expose_api_docs=False,
    )
    assert settings.environment == "production"
    assert settings.cors_origin_list == ["https://app.example.com"]
    assert settings.allowed_host_list == ["api.example.com"]


def test_production_rejects_wildcard_or_http_cors_origins():
    common = dict(
        environment="production",
        database_url="postgresql+psycopg://rea_user:replace-me@db.example.com:5432/rea",
        jwt_secret_key="K" * 48,
        allowed_hosts="api.example.com",
        secure_cookies=True,
        expose_api_docs=False,
    )
    with pytest.raises(ValidationError):
        Settings(**common, cors_origins="*")
    with pytest.raises(ValidationError):
        Settings(**common, cors_origins="http://app.example.com")


def test_relative_sqlite_database_path_is_stable_under_backend_directory():
    settings = Settings(
        database_url="sqlite+pysqlite:///./data/real_estate_dev.db"
    )
    resolved = settings.resolved_database_url

    expected = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "real_estate_dev.db"
    )

    # Compare the decoded database path, not the encoded URL string.
    resolved_path = make_url(resolved).database

    assert resolved_path is not None
    assert Path(resolved_path).resolve() == expected.resolve()
    assert expected.parent.is_dir()
