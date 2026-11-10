"""Version 1 of the HTTP API."""

from fastapi import APIRouter

from app.api.v1 import comparisons, health, trip_drafts, trips

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(trips.router)
api_router.include_router(comparisons.router)
api_router.include_router(trip_drafts.router)

__all__ = ["api_router"]
