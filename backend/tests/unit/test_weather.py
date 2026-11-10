"""Open-Meteo weather service with httpx.MockTransport (no network)."""

from collections.abc import Callable

import httpx
import pytest

from app.core.errors import ExternalServiceError, PlaceNotFoundError
from app.services.weather import OpenMeteoWeatherService, bad_for_cycling, describe_weather_code
from tests.fakes import FakeRouteProvider, make_weather

Handler = Callable[[httpx.Request], httpx.Response]
CURRENT = {
    "current": {
        "time": "2026-11-10T11:45",
        "temperature_2m": 2.6,
        "precipitation": 0.4,
        "wind_speed_10m": 3.5,
        "weather_code": 61,
    }
}


class Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now


def make_service(
    handler: Handler, provider: FakeRouteProvider | None = None, clock: Clock | None = None
) -> tuple[OpenMeteoWeatherService, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(record))
    service = OpenMeteoWeatherService(
        client, "https://meteo.test/", provider or FakeRouteProvider(), clock=clock or Clock()
    )
    return service, seen


def test_current_weather_is_parsed() -> None:
    service, seen = make_service(lambda _: httpx.Response(200, json=CURRENT))

    weather = service.current(54.35, 18.65, "Gdańsk")

    assert weather is not None
    assert (weather.location, weather.temperature_c, weather.precipitation_mm) == (
        "Gdańsk",
        2.6,
        0.4,
    )
    assert (weather.wind_kph, weather.weather_code, weather.description) == (3.5, 61, "rain")
    params = seen[0].url.params
    assert seen[0].url.path == "/v1/forecast"
    assert (params["latitude"], params["longitude"]) == ("54.35", "18.65")
    assert "temperature_2m" in params["current"]


@pytest.mark.parametrize(
    "handler",
    [
        lambda _: httpx.Response(500),
        lambda _: httpx.Response(200, json={"error": True}),
        lambda _: httpx.Response(200, text="nope"),
        lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request)),
    ],
    ids=["http-500", "missing-current", "not-json", "timeout"],
)
def test_failures_return_none(handler: Handler) -> None:
    service, _ = make_service(handler)

    assert service.current(50.0, 19.9, "Kraków") is None


def test_results_are_cached_per_location() -> None:
    clock = Clock()
    service, seen = make_service(lambda _: httpx.Response(200, json=CURRENT), clock=clock)

    service.current(50.061, 19.938, "Kraków")
    service.current(50.0612, 19.9381, "Kraków")
    assert len(seen) == 1

    clock.now = 601
    service.current(50.061, 19.938, "Kraków")
    assert len(seen) == 2


def test_failed_lookups_are_not_cached() -> None:
    responses = iter([httpx.Response(500), httpx.Response(200, json=CURRENT)])
    service, _ = make_service(lambda _: next(responses))

    assert service.current(50.0, 19.9, "Kraków") is None
    assert service.current(50.0, 19.9, "Kraków") is not None


def test_for_place_uses_the_geocoder() -> None:
    service, seen = make_service(lambda _: httpx.Response(200, json=CURRENT))

    weather = service.for_place("Kraków")

    assert weather is not None and weather.location == "Kraków"
    assert seen[0].url.params["latitude"] == "50.0647"


@pytest.mark.parametrize("error", [PlaceNotFoundError("Atlantis"), ExternalServiceError("geo")])
def test_for_place_returns_none_when_geocoding_fails(error: Exception) -> None:
    provider = FakeRouteProvider(error=error)  # type: ignore[arg-type]
    service, seen = make_service(lambda _: httpx.Response(200, json=CURRENT), provider)

    assert service.for_place("Atlantis") is None
    assert seen == []


@pytest.mark.parametrize(
    ("kwargs", "bad"),
    [
        ({}, False),
        ({"precipitation_mm": 1.2, "weather_code": 63}, True),
        ({"weather_code": 71}, True),  # snow
        ({"wind_kph": 45}, True),
        ({"temperature_c": -2}, True),
        ({"temperature_c": 35}, True),
    ],
)
def test_bad_for_cycling(kwargs: dict[str, float], bad: bool) -> None:
    assert (bad_for_cycling(make_weather(**kwargs)) is not None) is bad  # type: ignore[arg-type]


def test_describe_weather_code() -> None:
    assert describe_weather_code(0) == "clear sky"
    assert describe_weather_code(95) == "thunderstorm"
    assert describe_weather_code(None) is None
    assert describe_weather_code(42) is None
