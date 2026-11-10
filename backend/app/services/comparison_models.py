"""Plain dataclasses describing a comparison.

Shared by the comparison service, the snapshot mapping and (later) the AI tools.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.trip import TransportMode


@dataclass(frozen=True)
class RoutePoint:
    name: str
    lat: float | None
    lon: float | None


@dataclass(frozen=True)
class ComparedRoute:
    origin: RoutePoint
    destination: RoutePoint
    distance_km: float
    source: str  # "osrm" | "estimate" | "user"


@dataclass(frozen=True)
class ComparedOption:
    mode: TransportMode
    distance_km: float
    duration_min: int
    cost_pln: float
    co2_kg: float
    co2_saved_vs_car_kg: float
    """kg CO2 saved per person compared to driving alone in a petrol car (negative = more)."""
    practical: bool
    note: str | None


@dataclass(frozen=True)
class Highlights:
    greenest: TransportMode | None
    fastest: TransportMode | None
    cheapest: TransportMode | None


@dataclass(frozen=True)
class ComparisonResult:
    """A freshly computed comparison (not stored)."""

    route: ComparedRoute
    passengers: int
    options: list[ComparedOption]
    highlights: Highlights

    def option(self, mode: TransportMode) -> ComparedOption | None:
        return next((o for o in self.options if o.mode is mode), None)

    @property
    def solo_car_co2_kg(self) -> float:
        """CO2 for one person driving alone in a petrol car on this route."""
        option = self.options[0]
        return round(option.co2_kg + option.co2_saved_vs_car_kg, 2)


@dataclass(frozen=True)
class SavedComparison:
    """A stored comparison: the snapshot plus id, timestamp and advice."""

    id: int
    created_at: datetime
    route: ComparedRoute
    passengers: int
    options: list[ComparedOption]
    highlights: Highlights
    advice: dict[str, Any] | None

    def to_result(self) -> ComparisonResult:
        return ComparisonResult(self.route, self.passengers, self.options, self.highlights)


@dataclass(frozen=True)
class ComparisonSummary:
    id: int
    origin: str
    destination: str
    passengers: int
    distance_km: float
    created_at: datetime
    greenest_mode: TransportMode | None
    greenest_co2_kg: float | None
    solo_car_co2_kg: float
    recommended_mode: TransportMode | None
