"""The MCP server lists exactly the registry's tools and runs them through the registry."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import anyio
import pytest
from mcp import Client
from mcp_types.version import LATEST_HANDSHAKE_VERSION
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.testclient import TestClient

from app.ai.tools import ToolRegistry, stats_to_tool_data
from app.core.config import Settings
from app.mcp_server import build_mcp_http_app, build_mcp_registry, build_mcp_server
from app.models.trip import TransportMode
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreate
from app.services.stats import StatsRange, StatsService
from app.services.trip_service import TripService
from tests.fakes import FakeRouteProvider, FakeWeather, make_weather


@pytest.fixture(name="registry")
def registry_fixture(engine: Engine) -> ToolRegistry:
    return build_mcp_registry(FakeRouteProvider(), FakeWeather(make_weather()), engine)


def with_client[T](registry: ToolRegistry, use: Callable[[Client], Awaitable[T]]) -> T:
    async def run() -> T:
        async with Client(build_mcp_server(registry)) as client:
            return await use(client)

    return anyio.run(run)


def test_mcp_lists_exactly_the_registry_tools(registry: ToolRegistry) -> None:
    async def list_tools(client: Client) -> Any:
        return (await client.list_tools()).tools

    tools = with_client(registry, list_tools)

    assert [tool.name for tool in tools] == registry.names
    assert "get_trip_stats" in registry.names
    specs = {spec["name"]: spec for spec in registry.specs()}
    for tool in tools:
        assert tool.description == specs[tool.name]["description"]
        assert tool.input_schema == specs[tool.name]["parameters"]


def test_get_trip_stats_returns_the_dashboard_numbers(
    registry: ToolRegistry, session: Session
) -> None:
    repository = TripRepository(session)
    TripService(repository).create_trip(
        TripCreate(
            origin="Warszawa", destination="Kraków", distance_km=295, mode=TransportMode.TRAIN
        )
    )

    async def call(client: Client) -> Any:
        return await client.call_tool("get_trip_stats", {"range": "30d"})

    result = with_client(registry, call)

    assert result.is_error is False
    data = result.structured_content
    expected = stats_to_tool_data(StatsService(repository).get_stats(StatsRange.DAYS_30))
    assert data == expected
    assert data["totals"]["trips"] == 1
    assert data["to"] == datetime.now(UTC).date().isoformat()
    assert data["quote"]["co2_footprint"].endswith(" kg")
    assert '"get_trip_stats"' not in result.content[0].text  # the text block is the data
    assert '"totals"' in result.content[0].text


def test_tool_errors_come_back_as_error_results(registry: ToolRegistry) -> None:
    async def call(client: Client) -> Any:
        return await client.call_tool("get_trip_stats", {"range": "7d"})

    result = with_client(registry, call)

    assert result.is_error is True
    assert "Invalid arguments" in result.structured_content["error"]


def test_mcp_call_matches_a_direct_registry_call(registry: ToolRegistry) -> None:
    arguments = {"distance_km": 300, "mode": "car_petrol", "passengers": 2}

    async def call(client: Client) -> Any:
        return await client.call_tool("calculate_emissions", arguments)

    result = with_client(registry, call)

    assert result.structured_content == registry.run("calculate_emissions", arguments).data


# --- Streamable HTTP -----------------------------------------------------------------------------

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": LATEST_HANDSHAKE_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def http_client(registry: ToolRegistry) -> TestClient:
    settings = Settings(cors_origins=["http://localhost:5173"])
    app = build_mcp_http_app(build_mcp_server(registry), settings)
    return TestClient(app, base_url="http://localhost:8000")


def test_http_transport_accepts_the_web_app_origin(registry: ToolRegistry) -> None:
    with http_client(registry) as client:
        response = client.post(
            "/mcp", json=INITIALIZE, headers={**HEADERS, "Origin": "http://localhost:5173"}
        )

    assert response.status_code == 200
    assert response.headers.get("mcp-session-id")
    assert "ecoroute" in response.text


def test_http_transport_rejects_other_origins(registry: ToolRegistry) -> None:
    with http_client(registry) as client:
        response = client.post(
            "/mcp", json=INITIALIZE, headers={**HEADERS, "Origin": "http://evil.example"}
        )

    assert response.status_code == 403
