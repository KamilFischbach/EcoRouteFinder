"""Route lookup (distance and travel time between two places).

TODO:
- Provider abstraction (e.g. OpenRouteService / OSRM) behind a small Protocol.
- Fallback: great-circle distance times a per-mode detour factor when the provider is down.
- Exposed to the AI advisor as the `get_route` tool.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteInfo:
    distance_km: float
    duration_min: float


def get_route(origin: str, destination: str) -> RouteInfo:
    """Return distance and duration between two places. Not implemented yet."""
    raise NotImplementedError("TODO: routing provider")
