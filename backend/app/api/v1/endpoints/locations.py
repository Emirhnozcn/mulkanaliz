from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.location import Location
from app.models.user import User
from app.schemas.location import LocationCreate, LocationRead

router = APIRouter()


@router.post("", response_model=LocationRead, status_code=201)
def create_location(payload: LocationCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    parent = db.get(Location, payload.parent_id) if payload.parent_id is not None else None
    if payload.parent_id is not None and parent is None:
        raise NotFoundError("Üst konum bulunamadı.")
    expected_parent = {"province": None, "district": "province", "neighborhood": "district"}[payload.level]
    if expected_parent is None and payload.parent_id is not None:
        raise HTTPException(status_code=422, detail="Şehir kaydının üst konumu olamaz.")
    if expected_parent is not None and (parent is None or parent.level != expected_parent):
        raise HTTPException(status_code=422, detail="Konumun üst seviyesi geçersiz.")
    clean_name = " ".join(payload.name.strip().split())
    normalized = clean_name.replace("İ", "i").replace("I", "ı").lower()
    existing = db.scalar(select(Location).where(
        Location.parent_id == payload.parent_id,
        Location.level == payload.level,
        Location.normalized_name == normalized,
    ))
    if existing is not None:
        return existing
    location = Location(**{**payload.model_dump(), "name": clean_name, "normalized_name": normalized})
    db.add(location)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Concurrent requests may have created the same location; return that canonical row.
        existing = db.scalar(select(Location).where(Location.parent_id == payload.parent_id, Location.level == payload.level, Location.normalized_name == normalized))
        if existing is not None:
            return existing
        raise
    db.refresh(location)
    return location


@router.get("", response_model=list[LocationRead])
def list_locations(parent_id: int | None = Query(default=None), level: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    stmt = select(Location).order_by(Location.id).offset(offset).limit(limit)
    if parent_id is not None:
        stmt = stmt.where(Location.parent_id == parent_id)
    if level is not None:
        stmt = stmt.where(Location.level == level)
    return list(db.scalars(stmt).all())


@router.get("/{location_id}", response_model=LocationRead)
def get_location(location_id: int, db: Session = Depends(get_db)):
    location = db.get(Location, location_id)
    if location is None:
        raise NotFoundError("Konum bulunamadı.")
    return location
