"""Weather lookup used by the advisor (e.g. whether it is a good day to cycle).

TODO:
- Provider client (e.g. Open-Meteo, no API key) with timeout and caching.
- Graceful degradation: return None when the provider is down; callers must handle it.
- Exposed to the AI advisor as the `get_weather` tool.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherInfo:
    temperature_c: float
    precipitation_mm: float
    wind_kph: float


def get_weather(location: str) -> WeatherInfo | None:
    """Return current weather for a location. Not implemented yet."""
    raise NotImplementedError("TODO: weather provider")
