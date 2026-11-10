"""Tool registry: the ONLY place where tools for the advisor (and later an MCP server) are defined.

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
from app.services.comparison_models import ComparisonResult
from app.services.comparison_service import ComparisonService
from app.services.emissions import calculate_emissions
from app.services.weather import WeatherProvider

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


def comparison_to_tool_data(result: ComparisonResult) -> dict[str, Any]:
    """Compact, LLM-friendly view of a comparison (all values per person)."""
    return {
        "route": {
            "origin": result.route.origin.name,
            "destination": result.route.destination.name,
            "road_distance_km": result.route.distance_km,
            "distance_source": result.route.source,
        },
        "passengers": result.passengers,
        "values_are": "per person",
        "options": [
            {
                "mode": o.mode.value,
                "practical": o.practical,
                "co2_kg": o.co2_kg,
                "co2_saved_vs_driving_alone_kg": o.co2_saved_vs_car_kg,
                "duration_min": o.duration_min,
                "cost_pln": o.cost_pln,
                "distance_km": o.distance_km,
                **({"note": o.note} if o.note else {}),
            }
            for o in result.options
        ],
        "highlights": {k: (v.value if v else None) for k, v in asdict(result.highlights).items()},
    }


def build_tool_registry(comparisons: ComparisonService, weather: WeatherProvider) -> ToolRegistry:
    def compare_travel_options(args: CompareTravelOptionsArgs) -> dict[str, Any]:
        result = comparisons.compute(args.origin, args.destination, args.passengers)
        return comparison_to_tool_data(result)

    def get_weather(args: GetWeatherArgs) -> dict[str, Any]:
        info = weather.for_place(args.location)
        if info is None:
            raise ToolError(f"Weather is not available for '{args.location}' right now.")
        return asdict(info)

    def emissions(args: CalculateEmissionsArgs) -> dict[str, Any]:
        co2 = calculate_emissions(args.distance_km, args.mode, args.passengers)
        return {
            "mode": args.mode.value,
            "distance_km": args.distance_km,
            "passengers": args.passengers,
            "co2_kg_per_person": round(co2, 2),
        }

    return ToolRegistry(
        [
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
    )
