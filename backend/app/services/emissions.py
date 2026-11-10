"""Deterministic CO2, cost and time estimates. The single source of truth for emissions.

All results are **per person**:
- cars: the vehicle's emissions and cost are split between passengers,
- public transport and bikes: the per-passenger-km factor applies to each traveller.

Pure functions with plain inputs and dataclass outputs, so they can be reused as AI agent tools
or MCP tools. The LLM never computes these numbers.
"""

import math
from dataclasses import dataclass

from app.models.trip import TransportMode
from app.services.transport_factors import FACTORS

MIN_PASSENGERS = 1
MAX_PASSENGERS = 9


@dataclass(frozen=True)
class OptionEstimate:
    mode: TransportMode
    distance_km: float
    duration_min: int
    cost_pln: float
    co2_kg: float
    practical: bool
    note: str | None


def _validate(distance_km: float, passengers: int) -> None:
    if not math.isfinite(distance_km) or distance_km <= 0:
        raise ValueError("distance_km must be a positive number")
    if not MIN_PASSENGERS <= passengers <= MAX_PASSENGERS:
        raise ValueError(f"passengers must be between {MIN_PASSENGERS} and {MAX_PASSENGERS}")


def _per_person(
    value_per_km: float, distance_km: float, mode: TransportMode, passengers: int
) -> float:
    total = value_per_km * distance_km
    return total / passengers if FACTORS[mode].shared_by_passengers else total


def calculate_emissions(distance_km: float, mode: TransportMode, passengers: int = 1) -> float:
    """Return kg CO2e per person for travelling `distance_km` by `mode`."""
    _validate(distance_km, passengers)
    return _per_person(FACTORS[mode].co2_kg_per_km, distance_km, mode, passengers)


def estimate_cost(distance_km: float, mode: TransportMode, passengers: int = 1) -> float:
    """Return the approximate cost in PLN per person."""
    _validate(distance_km, passengers)
    return _per_person(FACTORS[mode].cost_pln_per_km, distance_km, mode, passengers)


def estimate_duration_min(
    distance_km: float, mode: TransportMode, driving_duration_min: float | None = None
) -> int:
    """Door-to-door minutes. Cars use the routing service's driving time when available."""
    factors = FACTORS[mode]
    if driving_duration_min is not None and factors.shared_by_passengers:
        moving = driving_duration_min
    else:
        moving = distance_km / factors.speed_kmh * 60
    return round(moving + factors.overhead_min)


def check_practical(distance_km: float, mode: TransportMode, passengers: int) -> str | None:
    """Return why `mode` is impractical for this trip, or None when it is practical."""
    factors = FACTORS[mode]
    if factors.min_practical_km is not None and distance_km < factors.min_practical_km:
        return f"Not worth flying under {factors.min_practical_km:.0f} km."
    if factors.max_practical_km is not None and distance_km > factors.max_practical_km:
        return f"Too far to cycle (over {factors.max_practical_km:.0f} km)."
    if factors.max_passengers is not None and passengers > factors.max_passengers:
        return f"A car seats up to {factors.max_passengers} people."
    return None


def estimate_option(
    mode: TransportMode,
    distance_km: float,
    passengers: int = 1,
    driving_duration_min: float | None = None,
) -> OptionEstimate:
    """Full per-person estimate for one mode over its own travel distance."""
    reason = check_practical(distance_km, mode, passengers)
    return OptionEstimate(
        mode=mode,
        distance_km=round(distance_km, 1),
        duration_min=estimate_duration_min(distance_km, mode, driving_duration_min),
        cost_pln=round(estimate_cost(distance_km, mode, passengers), 2),
        co2_kg=round(calculate_emissions(distance_km, mode, passengers), 2),
        practical=reason is None,
        note=reason,
    )
