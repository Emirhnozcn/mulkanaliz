from fastapi import APIRouter
from app.api.v1.endpoints import analytics, auth, exports, imports, locations, listings, users

auth_router = auth.router
api_router = APIRouter()
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
