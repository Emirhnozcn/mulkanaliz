from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.errors import ConflictError
from app.db.session import get_db
from app.schemas.import_listing import ImportListingRequest, ImportListingResult
from app.services.import_service import import_listing

router = APIRouter()


@router.post("/listing", response_model=ImportListingResult, status_code=200, responses={201: {"description": "İlan ilk kez oluşturuldu."}})
def post_import_listing(payload: ImportListingRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Import one listing explicitly confirmed by the user from an authorized source."""
    try:
        payload = payload.model_copy(update={"created_by": current_user.id})
        result = import_listing(db, payload, actor=current_user)
        # Idempotent updates return 200, first creation returns 201. FastAPI's route default is
        # overridden below by the response status when an existing source was found.
        from fastapi.responses import JSONResponse
        status_code = 201 if result["action"] == "created" else 200
        return JSONResponse(status_code=status_code, content=ImportListingResult(**result).model_dump(mode="json"))
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("İçe aktarma mevcut bir kaynak ilanıyla çakışıyor.") from exc
