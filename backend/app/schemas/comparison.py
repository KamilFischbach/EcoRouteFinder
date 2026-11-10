"""DTOs for the comparisons API. All CO2 and cost values are per person."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.models.trip import TransportMode
from app.schemas.trip import DistanceKm, Passengers, PlaceName


def _assume_utc(value: datetime) -> datetime:
    # SQLite drops tzinfo; values are always stored in UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_assume_utc)]
Preferences = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class ComparisonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: PlaceName
    destination: PlaceName
    passengers: Passengers = 1
    distance_km: DistanceKm | None = None
    """Optional road distance. When given, no geocoding or routing request is made."""


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RoutePointRead(_FromAttributes):
    name: str
    lat: float | None
    lon: float | None


class RouteRead(_FromAttributes):
    origin: RoutePointRead
    destination: RoutePointRead
    distance_km: float
    source: Literal["osrm", "estimate", "user"]


class ComparisonOptionRead(_FromAttributes):
    mode: TransportMode
    distance_km: float
    duration_min: int
    cost_pln: float
    co2_kg: float
    co2_saved_vs_car_kg: float
    practical: bool
    note: str | None


class HighlightsRead(_FromAttributes):
    greenest: TransportMode | None
    fastest: TransportMode | None
    cheapest: TransportMode | None


class AdviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferences: Preferences | None = None
    """Free text such as "I have luggage" or "cheapest please"."""


class WeatherRead(_FromAttributes):
    location: str
    temperature_c: float
    precipitation_mm: float
    wind_kph: float
    weather_code: int | None
    description: str | None


class ToolTraceRead(_FromAttributes):
    tool: str
    arguments: dict[str, Any]
    ok: bool


class AdviceRead(_FromAttributes):
    recommended_mode: TransportMode
    summary: str
    reasons: list[str]
    used_llm: bool
    model: str | None
    weather: WeatherRead | None
    preferences: str | None
    tool_trace: list[ToolTraceRead]
    created_at: UtcDatetime


class ComparisonRead(_FromAttributes):
    """A stored comparison: the snapshot taken when it was created, plus advice if any."""

    id: int
    created_at: UtcDatetime
    route: RouteRead
    passengers: int
    options: list[ComparisonOptionRead]
    highlights: HighlightsRead
    advice: AdviceRead | None


class ComparisonSummaryRead(_FromAttributes):
    """Lightweight row for the history list."""

    id: int
    origin: str
    destination: str
    passengers: int
    distance_km: float
    created_at: UtcDatetime
    greenest_mode: TransportMode | None
    greenest_co2_kg: float | None
    solo_car_co2_kg: float
    recommended_mode: TransportMode | None
