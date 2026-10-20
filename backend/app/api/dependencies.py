from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    settings = get_settings()
    token = credentials.credentials if credentials else request.cookies.get("rea_access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmanız gerekiyor.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"], options={"require": ["exp", "iat", "sub", "ver"], "verify_signature": True, "verify_exp": True, "verify_iat": True})
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Oturum geçersiz veya süresi dolmuş.", headers={"WWW-Authenticate": "Bearer"}) from exc
    token_version = payload.get("ver")
    if isinstance(token_version, bool) or not isinstance(token_version, int) or token_version < 0:
        raise HTTPException(status_code=401, detail="Oturum geçersiz veya süresi dolmuş.", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı veya devre dışı.", headers={"WWW-Authenticate": "Bearer"})
    if user.token_version != token_version or payload.get("role") != user.role:
        # Role changes must not silently elevate or preserve privileges in old tokens.
        raise HTTPException(status_code=401, detail="Oturum geçersiz veya süresi dolmuş.", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Bu işlem için yönetici yetkisi gerekiyor.")
    return user
