"""CO2 emission calculator: deterministic, the single source of truth for emissions.

TODO:
- Emission factors per transport mode (kg CO2e per passenger-km or per vehicle-km),
  with the data source documented next to each factor.
- Car modes: per-vehicle emissions split by passengers; public transport: per passenger.
- Pure functions only (no I/O) so they are trivially unit-testable.
- Exposed to the AI advisor as the `calculate_emissions` tool. The LLM never computes CO2 itself.
"""

from app.models.trip import TransportMode


def calculate_emissions(distance_km: float, mode: TransportMode, passengers: int) -> float:
    """Return total kg CO2 for the trip. Not implemented yet."""
    raise NotImplementedError("TODO: emission factors")
