"""Compare every transport mode for one route (per person), and keep a history of comparisons.

Distance per mode:
- cars and coach use the road distance (OSRM, estimate or the user's number),
- train, plane and bike use great-circle distance x the mode's detour factor.
When the user gives `distance_km`, it is treated as the road distance and no network call is made.

`compute()` never touches the database, so it can back an AI tool. `create()` computes and
stores a snapshot; history reads return that snapshot without recomputing.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.errors import NotFoundError, RouteTooShortError
from app.models.comparison import Comparison
from app.models.trip import TransportMode, utc_today
from app.repositories.comparison_repository import ComparisonRepository
from app.services import comparison_snapshot as snapshot
from app.services.comparison_models import (
    ComparedOption,
    ComparedRoute,
    ComparisonResult,
    ComparisonSummary,
    Highlights,
    RoutePoint,
    SavedComparison,
)
from app.services.emissions import OptionEstimate, estimate_option
from app.services.routing import RouteProvider
from app.services.transport_factors import FACTORS

__all__ = ["ComparisonService", "Highlights", "mode_distance_km", "pick_highlights"]

ROAD_MODES = frozenset({TransportMode.CAR_PETROL, TransportMode.CAR_EV, TransportMode.COACH})
MIN_ROUTE_KM = 1.0


@dataclass(frozen=True)
class _ResolvedRoute:
    route: ComparedRoute
    road_km: float
    great_circle_km: float
    driving_duration_min: float | None


def mode_distance_km(mode: TransportMode, road_km: float, great_circle_km: float) -> float:
    if mode in ROAD_MODES:
        return road_km
    return great_circle_km * FACTORS[mode].detour_factor


def pick_highlights(options: list[ComparedOption]) -> Highlights:
    practical = [option for option in options if option.practical]
    if not practical:
        return Highlights(greenest=None, fastest=None, cheapest=None)
    greenest = min(practical, key=lambda o: (o.co2_kg, o.duration_min))
    fastest = min(practical, key=lambda o: (o.duration_min, o.co2_kg))
    cheapest = min(practical, key=lambda o: (o.cost_pln, o.co2_kg))
    return Highlights(greenest=greenest.mode, fastest=fastest.mode, cheapest=cheapest.mode)


class ComparisonService:
    def __init__(
        self, route_provider: RouteProvider, repository: ComparisonRepository | None = None
    ) -> None:
        self._route_provider = route_provider
        self._repository = repository

    # --- computing (no database) ----------------------------------------------

    def compute(
        self,
        origin: str,
        destination: str,
        passengers: int = 1,
        distance_km: float | None = None,
    ) -> ComparisonResult:
        resolved = self._resolve_route(origin, destination, distance_km)
        if resolved.road_km < MIN_ROUTE_KM:
            raise RouteTooShortError(resolved.road_km)
        estimates = [self._estimate(mode, resolved, passengers) for mode in TransportMode]
        # Savings baseline: the same group going together by petrol car (per person). Using the
        # rounded estimate keeps the petrol car's own saving at exactly 0.
        baseline_kg = next(e.co2_kg for e in estimates if e.mode is TransportMode.CAR_PETROL)
        options = [_to_option(e, baseline_kg) for e in estimates]
        options.sort(key=lambda o: (o.co2_kg, o.duration_min))
        return ComparisonResult(
            route=resolved.route,
            passengers=passengers,
            options=options,
            highlights=pick_highlights(options),
        )

    # --- history ----------------------------------------------------------------

    def create(
        self,
        origin: str,
        destination: str,
        passengers: int = 1,
        distance_km: float | None = None,
        travelled_on: date | None = None,
    ) -> SavedComparison:
        """Compare and store. `travelled_on` is the day of the (planned) trip, default today."""
        result = self.compute(origin, destination, passengers, distance_km)
        record = snapshot.to_record(
            result, origin, destination, distance_km, travelled_on or utc_today()
        )
        return snapshot.to_saved(self._repo().save(record))

    def list_recent(self, limit: int = 20, offset: int = 0) -> list[ComparisonSummary]:
        return [snapshot.to_summary(r) for r in self._repo().list_recent(limit, offset)]

    def get(self, comparison_id: int) -> SavedComparison:
        return snapshot.to_saved(self._get_record(comparison_id))

    def delete(self, comparison_id: int) -> None:
        self._repo().delete(self._get_record(comparison_id))

    def save_advice(
        self, comparison_id: int, advice: dict[str, Any], recommended_mode: TransportMode
    ) -> SavedComparison:
        record = self._get_record(comparison_id)
        record.advice = advice
        record.recommended_mode = recommended_mode
        return snapshot.to_saved(self._repo().save(record))

    # --- helpers ----------------------------------------------------------------

    def _repo(self) -> ComparisonRepository:
        if self._repository is None:
            raise RuntimeError("ComparisonService was created without a repository")
        return self._repository

    def _get_record(self, comparison_id: int) -> Comparison:
        record = self._repo().get(comparison_id)
        if record is None:
            raise NotFoundError("Comparison", comparison_id)
        return record

    def _resolve_route(
        self, origin: str, destination: str, distance_km: float | None
    ) -> _ResolvedRoute:
        if distance_km is not None:
            route = ComparedRoute(
                origin=RoutePoint(origin, None, None),
                destination=RoutePoint(destination, None, None),
                distance_km=round(distance_km, 1),
                source="user",
            )
            great_circle = distance_km / FACTORS[TransportMode.CAR_PETROL].detour_factor
            return _ResolvedRoute(route, distance_km, great_circle, None)

        info = self._route_provider.get_route(origin, destination)
        route = ComparedRoute(
            origin=RoutePoint(info.origin.name, info.origin.lat, info.origin.lon),
            destination=RoutePoint(
                info.destination.name, info.destination.lat, info.destination.lon
            ),
            distance_km=round(info.road_km, 1),
            source=info.source,
        )
        return _ResolvedRoute(route, info.road_km, info.great_circle_km, info.driving_duration_min)

    @staticmethod
    def _estimate(mode: TransportMode, resolved: _ResolvedRoute, passengers: int) -> OptionEstimate:
        distance = mode_distance_km(mode, resolved.road_km, resolved.great_circle_km)
        return estimate_option(mode, distance, passengers, resolved.driving_duration_min)


def _to_option(estimate: OptionEstimate, baseline_kg: float) -> ComparedOption:
    return ComparedOption(
        mode=estimate.mode,
        distance_km=estimate.distance_km,
        duration_min=estimate.duration_min,
        cost_pln=estimate.cost_pln,
        co2_kg=estimate.co2_kg,
        co2_saved_vs_petrol_car_kg=round(baseline_kg - estimate.co2_kg, 2),
        practical=estimate.practical,
        note=estimate.note,
    )
