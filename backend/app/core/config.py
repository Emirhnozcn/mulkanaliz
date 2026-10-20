from functools import lru_cache
from pathlib import Path
from sqlalchemy.engine import make_url
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Real Estate Analytics API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    # Default SQLite file is resolved relative to the backend package, not the
    # shell's current working directory. This keeps local data across restarts.
    database_url: str = "sqlite+pysqlite:///./data/real_estate_dev.db"
    sql_echo: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    jwt_secret_key: str = "development-only-secret-key-change-before-deployment"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    secure_cookies: bool = False
    expose_api_docs: bool = True
    log_level: str = "INFO"
    office_registration_code: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


    @property
    def resolved_database_url(self) -> str:
        """Resolve relative SQLite paths against the backend directory and create the data folder."""
        url = make_url(self.database_url)
        if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
            return self.database_url
        database_path = Path(url.database)
        if not database_path.is_absolute():
            backend_root = Path(__file__).resolve().parents[2]
            database_path = (backend_root / database_path).resolve()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        # SQLAlchemy's SQLite URL format supports absolute Windows paths as
        # sqlite:///C:/... and POSIX paths as sqlite:////... .
        return url.set(database=str(database_path)).render_as_string(hide_password=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @model_validator(mode="after")
    def validate_production_configuration(self):
        if self.environment.lower() == "production":
            if len(self.jwt_secret_key) < 32 or self.jwt_secret_key.startswith("development-only"):
                raise ValueError("Production ortamında JWT_SECRET_KEY en az 32 karakterlik gerçek bir sır olmalıdır.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production ortamında PostgreSQL kullanılmalıdır.")
            if not self.cors_origin_list or "*" in self.cors_origin_list:
                raise ValueError("Production CORS_ORIGINS açıkça tanımlanmalıdır; wildcard yasaktır.")
            if any(not origin.startswith("https://") for origin in self.cors_origin_list):
                raise ValueError("Production CORS origin'leri HTTPS kullanmalıdır.")
            if not self.secure_cookies:
                raise ValueError("Production ortamında SECURE_COOKIES=true olmalıdır.")
            if self.expose_api_docs:
                raise ValueError("Production ortamında API dokümantasyonu için EXPOSE_API_DOCS=false ayarlayın.")
            if not self.allowed_host_list or any(host.lower() in {"localhost", "127.0.0.1", "*", "testserver"} for host in self.allowed_host_list):
                raise ValueError("Production ortamında ALLOWED_HOSTS gerçek sunucu adlarıyla açıkça tanımlanmalıdır.")
            for origin in self.cors_origin_list:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                if not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
                    raise ValueError("CORS_ORIGINS yalnızca tam origin değerleri içermelidir; path veya kimlik bilgisi kullanılamaz.")
                if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                    raise ValueError("Production CORS_ORIGINS yerel geliştirme adreslerini içeremez.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
