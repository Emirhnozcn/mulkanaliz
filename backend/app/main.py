import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.dependencies import get_current_user
from app.api.v1.router import api_router, auth_router
from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError
from app.db.session import engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.location import Location

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("rea.api")

def ensure_local_demo_account() -> None:
    """Create/reset a predictable demo account only in non-production environments."""
    if settings.environment.lower() == "production":
        return
    db = SessionLocal()
    try:
        # Populate the province selector on a fresh local database. Districts and
        # neighborhoods are user-entered because their boundaries/names change.
        provinces = [
            "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin",
            "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur",
            "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan",
            "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul",
            "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", "Kırşehir",
            "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş",
            "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop",
            "Şırnak", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"
        ]
        existing = set(db.scalars(select(Location.normalized_name).where(Location.level == "province")).all())
        for name in provinces:
            normalized = name.casefold()
            if normalized not in existing:
                db.add(Location(level="province", name=name, normalized_name=normalized))
        db.flush()
        user = db.scalar(select(User).where(User.username == "demo"))
        password = "demo12345678"  # local/demo only; change before any shared deployment
        if user is None:
            user = User(email="demo@emlak.local", username="demo", full_name="Demo Emlak Danışmanı", role="admin", password_hash=hash_password(password), is_active=True)
            db.add(user)
        else:
            user.email = "demo@emlak.local"
            user.full_name = "Demo Emlak Danışmanı"
            user.role = "admin"
            user.password_hash = hash_password(password)
            user.is_active = True
            user.token_version += 1
        db.commit()
        logger.info("local_demo_account_ready username=demo")
    except SQLAlchemyError as exc:
        db.rollback()
        # Migrations may not have been applied yet; API can start, but demo account cannot be seeded.
        logger.warning("local_demo_account_not_seeded error_type=%s; apply Alembic migrations", type(exc).__name__)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application_start environment=%s", settings.environment)
    ensure_local_demo_account()
    yield
    engine.dispose()

app = FastAPI(
    title=settings.app_name,
    description="Gayrimenkul ilanlarını ve fiyat geçmişini yöneten API.",
    version="1.0.0",
    openapi_url="/openapi.json" if settings.expose_api_docs else None,
    docs_url="/docs" if settings.expose_api_docs else None,
    redoc_url="/redoc" if settings.expose_api_docs else None,
    lifespan=lifespan,
)
if settings.environment.lower() == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

@app.middleware("http")
async def request_logging_and_security_headers(request: Request, call_next):
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_request_id if supplied_request_id and all(c.isalnum() or c in "._-" for c in supplied_request_id) and len(supplied_request_id) <= 100 else str(uuid.uuid4())
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        # Avoid logging exception strings/tracebacks here: database exceptions can contain query data.
        logger.error("request_failed request_id=%s method=%s path=%s error_type=%s", request_id, request.method, request.url.path, type(exc).__name__)
        response = JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "Beklenmeyen bir hata oluştu.", "request_id": request_id}})
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith(settings.api_v1_prefix) else "no-cache"
    if settings.environment.lower() == "production":
        # TLS is terminated at the trusted reverse proxy; production must serve HTTPS there.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    logger.info("request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s", request_id, request.method, request.url.path, response.status_code, elapsed_ms)
    return response

# Login/logout remain public. All business API endpoints require an active authenticated user.
app.include_router(auth_router, prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"])
app.include_router(api_router, prefix=settings.api_v1_prefix, dependencies=[Depends(get_current_user)])

@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/ready", tags=["health"])
def readiness() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("readiness_database_failed error_type=%s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "unavailable"})
    return {"status": "ready", "database": "ok"}

@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(exc)}})

@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"error": {"code": "conflict", "message": str(exc)}})

@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"error": {"code": "integrity_conflict", "message": "Kayıt benzersizlik veya ilişki kısıtını ihlal ediyor."}})

@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Never echo submitted values: validation payloads can contain passwords or tokens.
    details = [{"loc": error.get("loc"), "msg": error.get("msg"), "type": error.get("type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "İstek doğrulanamadı.", "details": details}})
