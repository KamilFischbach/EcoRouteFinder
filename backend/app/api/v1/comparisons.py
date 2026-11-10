"""Comparisons: compare all transport modes for a route and keep a history of results."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import ComparisonServiceDep
from app.schemas.comparison import ComparisonCreate, ComparisonRead, ComparisonSummaryRead

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_comparison(payload: ComparisonCreate, service: ComparisonServiceDep) -> ComparisonRead:
    saved = service.create(
        payload.origin, payload.destination, payload.passengers, payload.distance_km
    )
    return ComparisonRead.model_validate(saved)


@router.get("")
def list_comparisons(
    service: ComparisonServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ComparisonSummaryRead]:
    return [ComparisonSummaryRead.model_validate(s) for s in service.list_recent(limit, offset)]


@router.get("/{comparison_id}")
def get_comparison(comparison_id: int, service: ComparisonServiceDep) -> ComparisonRead:
    return ComparisonRead.model_validate(service.get(comparison_id))


@router.delete("/{comparison_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comparison(comparison_id: int, service: ComparisonServiceDep) -> None:
    service.delete(comparison_id)
