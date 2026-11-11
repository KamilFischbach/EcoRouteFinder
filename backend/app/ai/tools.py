"""Tool registry: the ONLY place where tools for the advisor and the MCP server are defined.

Each tool = name + description + Pydantic argument model + handler. Handlers are thin wrappers
around deterministic services; they never do maths themselves. `parameters` for the LLM come
from the argument model's JSON schema, and arguments are validated before a handler runs.
A failing tool never raises: the model gets `{"error": "..."}` back and can recover.
No FastAPI here.
"""

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.ai.llm_client import ToolSpec
from app.core.errors import AppError
from app.models.trip import TransportMode
from app.schemas.stats import StatsRead
from app.services.comparison_models import ComparedOption, ComparisonResult
from app.services.comparison_service import ComparisonService
from app.services.emissions import calculate_emissions
from app.services.formatting import (
    format_co2,
    format_co2_saving,
    format_cost,
    format_distance,
    format_duration,
    format_temperature,
)
from app.services.stats import DEFAULT_RANGE, Stats, StatsRange
from app.services.weather import WeatherInfo, WeatherProvider

logger = logging.getLogger(__name__)

Place = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Passengers = Annotated[int, Field(ge=1, le=9, description="Number of people travelling together")]


class ToolError(Exception):
    """Expected tool failure; its message is shown to the model."""


# --- argument models ------------------------------------------------------------------


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompareTravelOptionsArgs(_Args):
    origin: Place = Field(description="Start place, e.g. 'Warszawa'")
    destination: Place = Field(description="End place, e.g. 'Kraków'")
    passengers: Passengers = 1


class GetWeatherArgs(_Args):
    location: Place = Field(description="Town or city name")


class CalculateEmissionsArgs(_Args):
    distance_km: float = Field(gt=0, le=40_000, description="Distance in km")
    mode: TransportMode
    passengers: Passengers = 1


class GetTripStatsArgs(_Args):
    range: StatsRange = Field(
        default=DEFAULT_RANGE,
        description="Period: '30d', '90d', '12m' (by month) or 'all'",
    )


# --- registry -------------------------------------------------------------------------


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[Any], dict[str, Any]]

    def spec(self) -> ToolSpec:
        schema = self.args_model.model_json_schema()
        schema.pop("title", None)
        return {"name": self.name, "description": self.description, "parameters": schema}


@dataclass(frozen=True)
class ToolResult:
    name: str
    arguments: dict[str, Any]
    ok: bool
    data: dict[str, Any]


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return self._fail(name, arguments, f"Unknown tool '{name}'. Use one of: {self.names}")
        try:
            args = tool.args_model.model_validate(arguments)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in exc.errors()
            )
            return self._fail(name, arguments, f"Invalid arguments: {problems}")
        try:
            return ToolResult(name, arguments, True, tool.handler(args))
        except (ToolError, AppError, ValueError) as exc:
            message = exc.message if isinstance(exc, AppError) else str(exc)
            return self._fail(name, arguments, message)
        except Exception:  # a bug in a tool must not crash the conversation
            logger.exception("Tool %s crashed", name)
            return self._fail(name, arguments, "The tool failed unexpectedly.")

    @staticmethod
    def _fail(name: str, arguments: dict[str, Any], message: str) -> ToolResult:
        return ToolResult(name, arguments, False, {"error": message})


# --- handlers (thin wrappers around services) -----------------------------------------


SAVINGS_BASELINE = "the same group going together by petrol car"


def option_to_tool_data(option: ComparedOption) -> dict[str, Any]:
    """Raw values for checks and ready-to-quote strings for the model's answer."""
    return {
        "mode": option.mode.value,
        "practical": option.practical,
        "co2_kg": option.co2_kg,
        "co2_saved_vs_petrol_car_kg": option.co2_saved_vs_petrol_car_kg,
        "duration_min": option.duration_min,
        "cost_pln": option.cost_pln,
        "distance_km": option.distance_km,
        "quote": {
            "co2": format_co2(option.co2_kg),
            "co2_saved_vs_petrol_car": format_co2_saving(option.co2_saved_vs_petrol_car_kg),
            "duration": format_duration(option.duration_min),
            "cost": format_cost(option.cost_pln),
        },
        **({"note": option.note} if option.note else {}),
    }


def comparison_to_tool_data(result: ComparisonResult) -> dict[str, Any]:
    """Compact, LLM-friendly view of a comparison (all values per person)."""
    return {
        "route": {
            "origin": result.route.origin.name,
            "destination": result.route.destination.name,
            "road_distance_km": result.route.distance_km,
            "road_distance": format_distance(result.route.distance_km),
            "distance_source": result.route.source,
        },
        "passengers": result.passengers,
        "values_are": "per person",
        "co2_saved_is_compared_with": SAVINGS_BASELINE,
        "options": [option_to_tool_data(o) for o in result.options],
        "highlights": {k: (v.value if v else None) for k, v in asdict(result.highlights).items()},
    }


def weather_to_tool_data(info: WeatherInfo) -> dict[str, Any]:
    return {**asdict(info), "quote": {"temperature": format_temperature(info.temperature_c)}}


def stats_to_tool_data(stats: Stats) -> dict[str, Any]:
    """The same JSON as `GET /stats`, plus ready-to-quote strings."""
    totals = stats.totals
    return {
        **StatsRead.model_validate(stats).model_dump(mode="json", by_alias=True),
        "values_are": "per person",
        "co2_saved_is_compared_with": SAVINGS_BASELINE,
        "quote": {
            "co2_footprint": format_co2(totals.co2_kg),
            "co2_saved_vs_petrol_car": format_co2_saving(totals.co2_saved_kg),
            "distance": format_distance(totals.distance_km),
            "km_not_driven": format_distance(totals.km_not_driven),
            "eco_points": f"{totals.eco_points} points",
            "level": stats.level.name,
        },
    }


StatsSource = Callable[[StatsRange], Stats]
"""Returns the statistics for a range (opens its own DB session)."""


def build_tool_registry(
    comparisons: ComparisonService,
    weather: WeatherProvider,
    stats: StatsSource | None = None,
) -> ToolRegistry:
    """The advisor's tools; with `stats`, also `get_trip_stats` (used by the MCP server)."""

    def compare_travel_options(args: CompareTravelOptionsArgs) -> dict[str, Any]:
        result = comparisons.compute(args.origin, args.destination, args.passengers)
        return comparison_to_tool_data(result)

    def get_weather(args: GetWeatherArgs) -> dict[str, Any]:
        info = weather.for_place(args.location)
        if info is None:
            raise ToolError(f"Weather is not available for '{args.location}' right now.")
        return weather_to_tool_data(info)

    def emissions(args: CalculateEmissionsArgs) -> dict[str, Any]:
        co2 = calculate_emissions(args.distance_km, args.mode, args.passengers)
        return {
            "mode": args.mode.value,
            "distance_km": args.distance_km,
            "passengers": args.passengers,
            "co2_kg_per_person": round(co2, 2),
            "quote": {"co2_per_person": format_co2(co2)},
        }

    tools = [
        Tool(
            "compare_travel_options",
            "Compare time, cost and CO2 per person of all transport modes for a route. "
            "Use it for a different route or group size than in the context.",
            CompareTravelOptionsArgs,
            compare_travel_options,
        ),
        Tool(
            "get_weather",
            "Current weather (temperature, precipitation, wind) for a place.",
            GetWeatherArgs,
            get_weather,
        ),
        Tool(
            "calculate_emissions",
            "kg CO2 per person for a distance, transport mode and number of passengers, "
            "e.g. to answer 'what if we were 4?'.",
            CalculateEmissionsArgs,
            emissions,
        ),
    ]
    if stats is not None:
        tools.append(_trip_stats_tool(stats))
    return ToolRegistry(tools)


def _trip_stats_tool(stats: StatsSource) -> Tool:
    def get_trip_stats(args: GetTripStatsArgs) -> dict[str, Any]:
        return stats_to_tool_data(stats(args.range))

    return Tool(
        "get_trip_stats",
        "The user's saved trips for a period: carbon footprint, CO2 saved vs the same group by "
        "petrol car (net), km not driven, eco-points and level, a timeline, totals per mode and "
        "the change vs the previous period. Same numbers as the EcoRoute dashboard.",
        GetTripStatsArgs,
        get_trip_stats,
    )
