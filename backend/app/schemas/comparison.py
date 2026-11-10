"""DTOs for the comparisons API. All CO2 and cost values are per person."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.trip import TransportMode
from app.schemas.trip import DistanceKm, Passengers, PlaceName


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


class ComparisonRead(_FromAttributes):
    route: RouteRead
    passengers: int
    options: list[ComparisonOptionRead]
    highlights: HighlightsRead
