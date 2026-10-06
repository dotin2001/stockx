from fastapi import APIRouter

from app.api.v1 import admin, auth, cart, catalog, listings, watchlist

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
