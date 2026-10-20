from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.dependencies import require_admin
from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.models.listing import Listing, ListingPriceHistory
from app.schemas.user import UserCreate, UserRead

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where((User.email == payload.email) | (User.username == payload.username))):
        raise ConflictError("Bu e-posta veya kullanıcı adı zaten kayıtlı.")
    user = User(email=payload.email, username=payload.username, password_hash=hash_password(payload.password), full_name=payload.full_name.strip(), role=payload.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Kullanıcı kaydı mevcut verilerle çakışıyor.") from exc
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.id).offset(offset).limit(limit)).all())


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Kullanıcı bulunamadı.")
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, response: Response, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete an employee account only when it has no listing ownership/history dependencies."""
    if user_id == admin.id:
        raise ConflictError("Kendi hesabınızı silemezsiniz.")
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Kullanıcı bulunamadı.")
    if user.role == "admin" and db.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))) <= 1:
        raise ConflictError("Son aktif yönetici hesabı silinemez.")
    owned_listings = db.scalar(select(func.count(Listing.id)).where(Listing.created_by == user_id)) or 0
    if owned_listings:
        raise ConflictError(f"Bu kullanıcıya ait {owned_listings} ilan var. İlan sahipliğini başka bir çalışana devretmeden hesap silinemez. Veri kaybını önlemek için hesabı pasifleştirin veya önce ilanları devredin.")
    db.delete(user)
    db.commit()
    response.status_code = 204
    return response
