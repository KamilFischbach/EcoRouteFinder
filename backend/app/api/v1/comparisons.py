"""Comparisons endpoint: compare all transport modes for a route. Nothing is persisted."""

from fastapi import APIRouter

from app.api.deps import ComparisonServiceDep
from app.schemas.comparison import ComparisonCreate, ComparisonRead

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("")
def create_comparison(payload: ComparisonCreate, service: ComparisonServiceDep) -> ComparisonRead:
    comparison = service.compare(
        payload.origin, payload.destination, payload.passengers, payload.distance_km
    )
    return ComparisonRead.model_validate(comparison)
