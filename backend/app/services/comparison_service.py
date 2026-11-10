"""Compare every transport mode for one route (per person). Nothing is stored.

Distance per mode:
- cars and coach use the road distance (OSRM, estimate or the user's number),
- train, plane and bike use great-circle distance x the mode's detour factor.
When the user gives `distance_km`, it is treated as the road distance and no network call is made.
"""

from dataclasses import dataclass

from app.core.errors import RouteTooShortError
from app.models.trip import TransportMode
from app.services.emissions import OptionEstimate, calculate_emissions, estimate_option
from app.services.routing import RouteProvider
from app.services.transport_factors import FACTORS

ROAD_MODES = frozenset({TransportMode.CAR_PETROL, TransportMode.CAR_EV, TransportMode.COACH})
MIN_ROUTE_KM = 1.0


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
class Comparison:
    route: ComparedRoute
    passengers: int
    options: list[ComparedOption]
    highlights: Highlights


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
    def __init__(self, route_provider: RouteProvider) -> None:
        self._route_provider = route_provider

    def compare(
        self,
        origin: str,
        destination: str,
        passengers: int = 1,
        distance_km: float | None = None,
    ) -> Comparison:
        resolved = self._resolve_route(origin, destination, distance_km)
        if resolved.road_km < MIN_ROUTE_KM:
            raise RouteTooShortError(resolved.road_km)
        baseline_kg = calculate_emissions(resolved.road_km, TransportMode.CAR_PETROL, 1)
        options = [self._option(mode, resolved, passengers, baseline_kg) for mode in TransportMode]
        options.sort(key=lambda o: (o.co2_kg, o.duration_min))
        return Comparison(
            route=resolved.route,
            passengers=passengers,
            options=options,
            highlights=pick_highlights(options),
        )

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
    def _option(
        mode: TransportMode, resolved: _ResolvedRoute, passengers: int, baseline_kg: float
    ) -> ComparedOption:
        distance = mode_distance_km(mode, resolved.road_km, resolved.great_circle_km)
        estimate: OptionEstimate = estimate_option(
            mode, distance, passengers, resolved.driving_duration_min
        )
        return ComparedOption(
            mode=estimate.mode,
            distance_km=estimate.distance_km,
            duration_min=estimate.duration_min,
            cost_pln=estimate.cost_pln,
            co2_kg=estimate.co2_kg,
            co2_saved_vs_car_kg=round(baseline_kg - estimate.co2_kg, 2),
            practical=estimate.practical,
            note=estimate.note,
        )
