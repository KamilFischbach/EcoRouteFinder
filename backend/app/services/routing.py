"""Route lookup: geocode two places and get the driving distance and time between them.

- `RouteProvider` is the interface services depend on (tests use a fake).
- `OsmRouteProvider` uses OpenStreetMap Nominatim for geocoding and the public OSRM server for
  driving routes.
- Fallback: when OSRM fails, the road distance is estimated as great-circle distance x the car
  detour factor and the result is marked `source="estimate"`.
- Unknown place -> `PlaceNotFoundError`; geocoder unreachable -> `ExternalServiceError`.

Plain dataclasses in and out, no FastAPI, so this can also back an AI agent or MCP tool.
"""

import logging
import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx

from app.core.config import Settings
from app.core.errors import ExternalServiceError, PlaceNotFoundError
from app.models.trip import TransportMode
from app.services.transport_factors import FACTORS

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088
RouteSource = Literal["osrm", "estimate"]


@dataclass(frozen=True)
class Place:
    query: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteInfo:
    origin: Place
    destination: Place
    great_circle_km: float
    road_km: float
    driving_duration_min: float | None
    source: RouteSource


class RouteProvider(Protocol):
    def get_route(self, origin: str, destination: str) -> RouteInfo: ...


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class OsmRouteProvider:
    def __init__(
        self,
        client: httpx.Client,
        geocoder_url: str,
        routing_url: str,
        cache_size: int = 256,
        min_geocode_interval_s: float = 1.0,
    ) -> None:
        self._client = client
        self._geocoder_url = geocoder_url.rstrip("/")
        self._routing_url = routing_url.rstrip("/")
        self._cache: OrderedDict[str, Place] = OrderedDict()
        self._cache_size = cache_size
        # Nominatim's usage policy allows at most 1 request per second.
        self._min_interval_s = min_geocode_interval_s
        self._last_request_at = 0.0
        self._lock = threading.Lock()

    def get_route(self, origin: str, destination: str) -> RouteInfo:
        start = self.geocode(origin)
        end = self.geocode(destination)
        great_circle = haversine_km(start.lat, start.lon, end.lat, end.lon)
        driving = self._drive(start, end)
        if driving is None:
            road_km = great_circle * FACTORS[TransportMode.CAR_PETROL].detour_factor
            return RouteInfo(start, end, great_circle, road_km, None, "estimate")
        road_km, duration_min = driving
        return RouteInfo(start, end, great_circle, road_km, duration_min, "osrm")

    def geocode(self, query: str) -> Place:
        key = " ".join(query.lower().split())
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached
        place = self._fetch_place(query)
        self._remember(key, place)
        return place

    def _fetch_place(self, query: str) -> Place:
        self._throttle()
        try:
            response = self._client.get(
                f"{self._geocoder_url}/search",
                params={"q": query, "format": "jsonv2", "limit": 1},
            )
            response.raise_for_status()
            results: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Geocoder request failed: %s", exc)
            raise ExternalServiceError("geocoding") from exc
        if not isinstance(results, list) or not results:
            raise PlaceNotFoundError(query)
        first = results[0]
        return Place(
            query=query,
            name=str(first.get("name") or first.get("display_name") or query),
            lat=float(first["lat"]),
            lon=float(first["lon"]),
        )

    def _drive(self, start: Place, end: Place) -> tuple[float, float] | None:
        """Return (km, minutes) by car, or None if OSRM fails or finds no route."""
        coords = f"{start.lon},{start.lat};{end.lon},{end.lat}"
        try:
            response = self._client.get(
                f"{self._routing_url}/route/v1/driving/{coords}", params={"overview": "false"}
            )
            response.raise_for_status()
            body: Any = response.json()
            route = body["routes"][0] if body.get("code") == "Ok" else None
            if route is None:
                return None
            return float(route["distance"]) / 1000, float(route["duration"]) / 60
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning("Routing request failed, using estimate: %s", exc)
            return None

    def _remember(self, key: str, place: Place) -> None:
        self._cache[key] = place
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def _throttle(self) -> None:
        with self._lock:
            wait = self._last_request_at + self._min_interval_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()


def build_route_provider(settings: Settings) -> OsmRouteProvider:
    client = httpx.Client(
        timeout=settings.http_timeout_s,
        headers={"User-Agent": settings.http_user_agent},
        follow_redirects=True,
    )
    return OsmRouteProvider(client, settings.geocoder_url, settings.routing_url)
