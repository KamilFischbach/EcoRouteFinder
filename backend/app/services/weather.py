"""Current weather from Open-Meteo (no API key), used by the advisor.

- Coordinates come from the comparison, or from the existing geocoder (`Geocoder` protocol,
  implemented by `OsmRouteProvider`), so place lookup isn't duplicated.
- Short in-memory cache per location.
- Never raises for network problems: returns None and callers carry on without weather.

Plain dataclasses in and out, so this can back an AI agent tool or an MCP tool.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.core.errors import AppError
from app.services.routing import Place

logger = logging.getLogger(__name__)

CACHE_TTL_S = 600.0
CACHE_MAX_ENTRIES = 256

# When cycling is a bad idea (used by the rule-based advisor).
BIKE_MAX_PRECIPITATION_MM = 0.2  # per 15-minute interval, i.e. more than a light drizzle
BIKE_MAX_WIND_KPH = 30.0
BIKE_MIN_TEMPERATURE_C = 3.0
BIKE_MAX_TEMPERATURE_C = 32.0
# WMO weather codes for rain, snow and thunderstorms.
WET_WEATHER_CODES = frozenset({*range(51, 68), *range(71, 78), *range(80, 87), 95, 96, 99})

_WMO_DESCRIPTIONS: list[tuple[range, str]] = [
    (range(0, 1), "clear sky"),
    (range(1, 3), "partly cloudy"),
    (range(3, 4), "overcast"),
    (range(45, 49), "fog"),
    (range(51, 58), "drizzle"),
    (range(61, 68), "rain"),
    (range(71, 78), "snow"),
    (range(80, 83), "rain showers"),
    (range(85, 87), "snow showers"),
    (range(95, 100), "thunderstorm"),
]


@dataclass(frozen=True)
class WeatherInfo:
    location: str
    temperature_c: float
    precipitation_mm: float
    wind_kph: float
    weather_code: int | None
    description: str | None


class Geocoder(Protocol):
    def geocode(self, query: str) -> Place: ...


class WeatherProvider(Protocol):
    def current(self, lat: float, lon: float, location: str) -> WeatherInfo | None: ...

    def for_place(self, location: str) -> WeatherInfo | None: ...


def describe_weather_code(code: int | None) -> str | None:
    if code is None:
        return None
    return next((text for codes, text in _WMO_DESCRIPTIONS if code in codes), None)


def bad_for_cycling(weather: WeatherInfo) -> str | None:
    """Short reason why cycling is a bad idea in this weather, or None."""
    if weather.precipitation_mm > BIKE_MAX_PRECIPITATION_MM or (
        weather.weather_code in WET_WEATHER_CODES
    ):
        return f"{weather.description or 'rain'} in {weather.location}"
    if weather.wind_kph > BIKE_MAX_WIND_KPH:
        return f"strong wind ({weather.wind_kph:.0f} km/h) in {weather.location}"
    if weather.temperature_c < BIKE_MIN_TEMPERATURE_C:
        return f"cold ({weather.temperature_c:.0f} °C) in {weather.location}"
    if weather.temperature_c > BIKE_MAX_TEMPERATURE_C:
        return f"heat ({weather.temperature_c:.0f} °C) in {weather.location}"
    return None


class OpenMeteoWeatherService:
    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        geocoder: Geocoder,
        ttl_s: float = CACHE_TTL_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._geocoder = geocoder
        self._ttl_s = ttl_s
        self._clock = clock
        self._cache: dict[tuple[float, float], tuple[WeatherInfo, float]] = {}

    def for_place(self, location: str) -> WeatherInfo | None:
        try:
            place = self._geocoder.geocode(location)
        except AppError as exc:  # unknown place or geocoder down
            logger.info("Weather: could not locate %r: %s", location, exc.message)
            return None
        return self.current(place.lat, place.lon, place.name)

    def current(self, lat: float, lon: float, location: str) -> WeatherInfo | None:
        key = (round(lat, 2), round(lon, 2))
        cached = self._cache.get(key)
        now = self._clock()
        if cached is not None and now - cached[1] < self._ttl_s:
            return cached[0]
        weather = self._fetch(lat, lon, location)
        if weather is not None:
            if len(self._cache) >= CACHE_MAX_ENTRIES:
                self._cache.clear()
            self._cache[key] = (weather, now)
        return weather

    def _fetch(self, lat: float, lon: float, location: str) -> WeatherInfo | None:
        params: dict[str, str | float] = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation,wind_speed_10m,weather_code",
        }
        try:
            response = self._client.get(f"{self._base_url}/v1/forecast", params=params)
            response.raise_for_status()
            current: Any = response.json()["current"]
            code = current.get("weather_code")
            return WeatherInfo(
                location=location,
                temperature_c=float(current["temperature_2m"]),
                precipitation_mm=float(current["precipitation"]),
                wind_kph=float(current["wind_speed_10m"]),
                weather_code=int(code) if code is not None else None,
                description=describe_weather_code(int(code) if code is not None else None),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Weather request failed: %s", exc)
            return None


def build_weather_service(settings: Settings, geocoder: Geocoder) -> OpenMeteoWeatherService:
    client = httpx.Client(
        timeout=settings.http_timeout_s, headers={"User-Agent": settings.http_user_agent}
    )
    return OpenMeteoWeatherService(client, settings.weather_url, geocoder)
