"""Test doubles shared by unit and API tests."""

from typing import Any

from app.ai.llm_client import ChatMessage, LLMError, LLMResponse, ToolCall, ToolSpec
from app.core.errors import AppError
from app.services.routing import Place, RouteInfo, RouteSource

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
