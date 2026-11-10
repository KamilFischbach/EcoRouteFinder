"""DTOs for the dashboard statistics API. Mirrors `services/stats.py`."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.trip import TransportMode
from app.services.stats import Granularity, StatsRange


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StatsTotalsRead(_FromAttributes):
    trips: int
    distance_km: float
    co2_kg: float = Field(description="Carbon footprint, kg CO2 per person")
    co2_saved_kg: float = Field(
        description="Net kg CO2 saved per person vs the same group by petrol car (can be < 0)"
    )
    km_not_driven: float = Field(description="Distance of trips not made by petrol car")
    eco_points: int


class LevelRead(_FromAttributes):
    name: str
    points: int
    next_level_name: str | None
    next_level_at: int | None
    progress: float = Field(ge=0, le=1)


class TimelinePointRead(_FromAttributes):
    period_start: date
    co2_kg: float
    co2_saved_kg: float
    trips: int


class ModeStatsRead(_FromAttributes):
    mode: TransportMode
    trips: int
    co2_kg: float
    distance_km: float


class PreviousPeriodRead(_FromAttributes):
    date_from: date = Field(serialization_alias="from")
    date_to: date = Field(serialization_alias="to")
    totals: StatsTotalsRead
    co2_change_pct: float | None
    saved_change_pct: float | None


class BestTripRead(_FromAttributes):
    id: int | None
    origin: str
    destination: str
    mode: TransportMode
    travelled_on: date
    distance_km: float
    passengers: int
    co2_kg: float
    co2_saved_kg: float


class StatsRead(_FromAttributes):
    range: StatsRange
    granularity: Granularity = Field(description="week for 30d/90d, month for 12m/all")
    date_from: date = Field(serialization_alias="from")
    date_to: date = Field(serialization_alias="to")
    totals: StatsTotalsRead
    level: LevelRead
    timeline: list[TimelinePointRead]
    by_mode: list[ModeStatsRead]
    previous_period: PreviousPeriodRead | None
    best_trip: BestTripRead | None
