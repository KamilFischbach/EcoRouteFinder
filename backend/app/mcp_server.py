"""MCP server: exposes the tool registry from `ai/tools.py` over the Model Context Protocol.

Tools are not defined here. Every tool of the registry is listed with its name, description and
the JSON schema of its Pydantic argument model, and a call goes through `ToolRegistry.run`
(validation + error handling), so MCP clients get exactly what the EcoAdvisor gets, plus
`get_trip_stats`. All tools are read-only: nothing here saves or deletes data.

Two transports, one server definition:
- stdio, for desktop clients and the MCP Inspector: `python -m app.mcp_server`
- Streamable HTTP at `/mcp`, mounted into the FastAPI app (`main.py`) for the web UI.
"""

import json
from typing import Any

import anyio
import mcp_types as types
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.applications import Starlette

from app.ai.tools import ToolRegistry, build_tool_registry
from app.core.config import Settings, get_settings
from app.db import engine, init_db
from app.repositories.trip_repository import TripRepository
from app.services.comparison_service import ComparisonService
from app.services.routing import RouteProvider, build_route_provider
from app.services.stats import Stats, StatsRange, StatsService
from app.services.weather import WeatherProvider, build_weather_service

SERVER_NAME = "ecoroute"
SERVER_VERSION = "0.1.0"
MCP_PATH = "/mcp"
INSTRUCTIONS = (
    "EcoRoute tools. All CO2 and cost values are per person. Savings compare with the same "
    "group going together by petrol car. Quote the ready-made strings under `quote`."
)
LOCAL_HOSTS = ["localhost:*", "127.0.0.1:*", "[::1]:*"]


def build_mcp_registry(
    route_provider: RouteProvider, weather: WeatherProvider, engine: Engine
) -> ToolRegistry:
    """The registry with `get_trip_stats`; each stats call opens its own DB session."""

    def read_stats(stats_range: StatsRange) -> Stats:
        with Session(engine) as session:
            return StatsService(TripRepository(session)).get_stats(stats_range)

    return build_tool_registry(ComparisonService(route_provider), weather, read_stats)


def build_mcp_server(registry: ToolRegistry) -> Server[Any]:
    tools = [
        types.Tool(
            name=spec["name"], description=spec["description"], input_schema=spec["parameters"]
        )
        for spec in registry.specs()
    ]

    async def list_tools(
        _ctx: ServerRequestContext[Any], _params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tools)

    async def call_tool(
        _ctx: ServerRequestContext[Any], params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        # Handlers are synchronous (HTTP calls, SQLite), so keep them off the event loop.
        result = await anyio.to_thread.run_sync(registry.run, params.name, params.arguments or {})
        return types.CallToolResult(
            content=[types.TextContent(text=json.dumps(result.data, ensure_ascii=False))],
            structured_content=result.data,
            is_error=not result.ok,
        )

    return Server(
        SERVER_NAME,
        version=SERVER_VERSION,
        instructions=INSTRUCTIONS,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


def build_mcp_http_app(server: Server[Any], settings: Settings) -> Starlette:
    """Streamable HTTP endpoint at `/mcp`. Only local hosts and the configured CORS origins
    may call it (DNS rebinding protection)."""
    return server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        transport_security=TransportSecuritySettings(
            allowed_hosts=LOCAL_HOSTS, allowed_origins=settings.cors_origins
        ),
    )


async def _serve_stdio(server: Server[Any]) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    settings = get_settings()
    init_db()
    route_provider = build_route_provider(settings)
    weather = build_weather_service(settings, route_provider)
    server = build_mcp_server(build_mcp_registry(route_provider, weather, engine))
    anyio.run(_serve_stdio, server)


if __name__ == "__main__":
    main()
