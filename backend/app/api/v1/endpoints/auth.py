from typing import Annotated
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from app.schemas.user import UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    """Register an office employee only when they know the private office registration code."""
    settings = get_settings()
    if not settings.office_registration_code or not hmac.compare_digest(payload.registration_code, settings.office_registration_code):
        raise HTTPException(status_code=403, detail="Ofis kayıt kodu geçersiz.")
    if db.scalar(select(User.id).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="Bu kullanıcı adı zaten kayıtlı.")
    # Email is not collected during signup; keep a non-deliverable internal placeholder for legacy schema/token compatibility.
    internal_email = f"{payload.username}@users.invalid"
    user = User(email=internal_email, username=payload.username, password_hash=hash_password(payload.password), full_name=payload.full_name.strip(), role="agent")
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Annotated[Session, Depends(get_db)]):
    user = db.scalar(select(User).where(User.username == payload.username))
    # Do not reveal whether the account exists or is inactive.
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya parola hatalı.", headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token(user.id, user.role, user.email, user.token_version)
    settings = get_settings()
    response.set_cookie(
        key="rea_access_token", value=token, httponly=True, secure=settings.secure_cookies,
        samesite="lax", max_age=settings.access_token_expire_minutes * 60, path="/",
    )
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    # Revoke all copies/sessions of this user's token family server-side.
    user.token_version += 1
    db.add(user)
    db.commit()
    settings = get_settings()
    response.delete_cookie("rea_access_token", path="/", httponly=True, secure=settings.secure_cookies, samesite="lax")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserRead)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.get("/office-registration-code")
def get_office_registration_code(user: Annotated[User, Depends(require_admin)]):
    """Return the office invite code only to authenticated administrators."""
    code = get_settings().office_registration_code
    if not code:
        raise HTTPException(status_code=404, detail="Ofis kayıt kodu yapılandırılmamış. Backend .env dosyasında OFFICE_REGISTRATION_CODE ayarlayın.")
    return {"registration_code": code}
