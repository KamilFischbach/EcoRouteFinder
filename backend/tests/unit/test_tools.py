"""Tool registry: specs from Pydantic, validation and errors returned as data."""

from typing import Any

import pytest

from app.ai.tools import GetWeatherArgs, Tool, ToolRegistry, build_tool_registry
from app.core.errors import PlaceNotFoundError
from app.services.comparison_service import ComparisonService
from tests.fakes import FakeRouteProvider, FakeWeather, make_weather


def registry(
    provider: FakeRouteProvider | None = None, weather: FakeWeather | None = None
) -> ToolRegistry:
    return build_tool_registry(
        ComparisonService(provider or FakeRouteProvider()), weather or FakeWeather(make_weather())
    )


def test_specs_come_from_argument_models() -> None:
    specs = {spec["name"]: spec for spec in registry().specs()}

    assert set(specs) == {"compare_travel_options", "get_weather", "calculate_emissions"}
    emissions = specs["calculate_emissions"]["parameters"]
    assert emissions["required"] == ["distance_km", "mode"]
    assert emissions["properties"]["distance_km"]["exclusiveMinimum"] == 0
    assert "title" not in emissions


def test_calculate_emissions_tool() -> None:
    result = registry().run(
        "calculate_emissions", {"distance_km": 100, "mode": "car_petrol", "passengers": 2}
    )

    assert result.ok is True
    assert result.data == {
        "mode": "car_petrol",
        "distance_km": 100,
        "passengers": 2,
        "co2_kg_per_person": 8.08,
    }


def test_compare_tool_uses_the_comparison_service_without_saving() -> None:
    provider = FakeRouteProvider()
    result = registry(provider).run(
        "compare_travel_options", {"origin": "Warszawa", "destination": "Kraków", "passengers": 2}
    )

    assert result.ok is True
    assert provider.calls == [("Warszawa", "Kraków")]
    assert result.data["values_are"] == "per person"
    assert result.data["highlights"]["greenest"] == "train"
    train = next(o for o in result.data["options"] if o["mode"] == "train")
    assert train == {
        "mode": "train",
        "practical": True,
        "co2_kg": 9.35,
        "co2_saved_vs_driving_alone_kg": 38.04,
        "duration_min": 217,
        "cost_pln": 90.72,
        "distance_km": 302.4,
    }


def test_weather_tool() -> None:
    result = registry().run("get_weather", {"location": "Gdańsk"})

    assert result.ok is True
    assert result.data["location"] == "Gdańsk"
    assert result.data["temperature_c"] == 15.0


@pytest.mark.parametrize(
    ("name", "arguments", "error_start"),
    [
        ("book_ticket", {}, "Unknown tool 'book_ticket'"),
        ("calculate_emissions", {"distance_km": 0, "mode": "train"}, "Invalid arguments"),
        ("calculate_emissions", {"distance_km": 10, "mode": "rocket"}, "Invalid arguments"),
        ("get_weather", {"location": "Kraków", "units": "F"}, "Invalid arguments"),
        ("compare_travel_options", {"origin": "A"}, "Invalid arguments"),
    ],
)
def test_bad_calls_return_errors(name: str, arguments: dict[str, Any], error_start: str) -> None:
    result = registry().run(name, arguments)

    assert result.ok is False
    assert result.data["error"].startswith(error_start)
    assert result.arguments == arguments


def test_service_errors_become_tool_errors() -> None:
    provider = FakeRouteProvider(error=PlaceNotFoundError("Atlantyda"))

    result = registry(provider).run(
        "compare_travel_options", {"origin": "Warszawa", "destination": "Atlantyda"}
    )

    assert result.ok is False
    assert result.data == {"error": "Could not find a place called 'Atlantyda'"}


def test_missing_weather_is_a_tool_error() -> None:
    result = registry(weather=FakeWeather(None)).run("get_weather", {"location": "Kraków"})

    assert result.ok is False
    assert "not available" in result.data["error"]


def test_crashing_handler_does_not_raise() -> None:
    def boom(_: object) -> dict[str, Any]:
        raise RuntimeError("bug")

    tools = ToolRegistry([Tool("boom", "Crashes", GetWeatherArgs, boom)])

    result = tools.run("boom", {"location": "x"})

    assert result.ok is False
    assert result.data == {"error": "The tool failed unexpectedly."}
