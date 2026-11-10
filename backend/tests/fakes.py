"""Test doubles shared by unit and API tests."""

from dataclasses import replace
from typing import Any

from app.ai.llm_client import ChatMessage, LLMError, LLMResponse, ToolCall, ToolSpec
from app.core.errors import AppError
from app.services.routing import Place, RouteInfo, RouteSource
from app.services.weather import WeatherInfo, describe_weather_code

ScriptStep = LLMResponse | Exception


class FakeLLMClient:
    """Plays back a script of responses (or exceptions) and records every request."""

    def __init__(
        self, script: list[ScriptStep] | None = None, available: bool = True, model: str = "fake:1b"
    ) -> None:
        self.script = list(script or [])
        self.available = available
        self.model = model
        self.requests: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return self.available

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        self.requests.append(
            {"messages": list(messages), "tools": tools, "response_schema": response_schema}
        )
        if not self.script:
            raise LLMError("FakeLLMClient script is exhausted")
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def reply(content: str) -> LLMResponse:
    return LLMResponse(content=content)


def call_tool(name: str, **arguments: Any) -> LLMResponse:
    return LLMResponse(content="", tool_calls=[ToolCall(name=name, arguments=arguments)])


def make_route(
    origin: str = "Warszawa",
    destination: str = "Kraków",
    great_circle_km: float = 252.0,
    road_km: float = 293.4,
    driving_duration_min: float | None = 180.0,
    source: RouteSource = "osrm",
) -> RouteInfo:
    return RouteInfo(
        origin=Place(origin, origin, 52.2297, 21.0122),
        destination=Place(destination, destination, 50.0647, 19.9450),
        great_circle_km=great_circle_km,
        road_km=road_km,
        driving_duration_min=driving_duration_min,
        source=source,
    )


class FakeRouteProvider:
    """Returns a fixed route or raises a fixed error, and records every call."""

    def __init__(self, route: RouteInfo | None = None, error: AppError | None = None) -> None:
        self.route = route or make_route()
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def get_route(self, origin: str, destination: str) -> RouteInfo:
        self.calls.append((origin, destination))
        if self.error is not None:
            raise self.error
        return self.route

    def geocode(self, query: str) -> Place:
        if self.error is not None:
            raise self.error
        if query == self.route.destination.query:
            return self.route.destination
        return Place(query, query, 52.0, 19.0)


class FakeWeather:
    """WeatherProvider double: fixed weather (or None) and a record of lookups."""

    def __init__(self, weather: WeatherInfo | None = None) -> None:
        self.weather = weather
        self.lookups: list[str] = []

    def current(self, lat: float, lon: float, location: str) -> WeatherInfo | None:
        self.lookups.append(location)
        return replace(self.weather, location=location) if self.weather else None

    def for_place(self, location: str) -> WeatherInfo | None:
        return self.current(0.0, 0.0, location)


def make_weather(
    temperature_c: float = 15.0,
    precipitation_mm: float = 0.0,
    wind_kph: float = 10.0,
    weather_code: int | None = 1,
) -> WeatherInfo:
    return WeatherInfo(
        location="Kraków",
        temperature_c=temperature_c,
        precipitation_mm=precipitation_mm,
        wind_kph=wind_kph,
        weather_code=weather_code,
        description=describe_weather_code(weather_code),
    )
