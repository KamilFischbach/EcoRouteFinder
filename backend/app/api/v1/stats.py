"""Dashboard statistics endpoint. Thin: parse the range, call the service, shape the output."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import StatsServiceDep
from app.schemas.stats import StatsRead
from app.services.stats import DEFAULT_RANGE, StatsRange

router = APIRouter(prefix="/stats", tags=["stats"])

RangeParam = Annotated[StatsRange, Query(alias="range", description="30d, 90d, 12m or all")]


@router.get("")
def get_stats(service: StatsServiceDep, stats_range: RangeParam = DEFAULT_RANGE) -> StatsRead:
    return StatsRead.model_validate(service.get_stats(stats_range))
