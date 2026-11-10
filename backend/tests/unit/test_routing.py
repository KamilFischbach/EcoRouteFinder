"""OsmRouteProvider tests. No network: httpx.MockTransport answers every request."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import ExternalServiceError, PlaceNotFoundError
from app.services.routing import OsmRouteProvider, build_route_provider, haversine_km

GEOCODER = "https://geo.test"
ROUTER = "https://route.test"

PLACES: dict[str, dict[str, Any]] = {
    "warszawa": {"lat": "52.2297", "lon": "21.0122", "name": "Warszawa"},
    "kraków": {"lat": "50.0647", "lon": "19.9450", "name": "Kraków"},
}

Handler = Callable[[httpx.Request], httpx.Response]


def geocoder_ok(request: httpx.Request) -> httpx.Response:
    place = PLACES.get(request.url.params["q"].lower())
    return httpx.Response(200, json=[place] if place else [])


def osrm_ok(_: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, json={"code": "Ok", "routes": [{"distance": 293_400.0, "duration": 10_800.0}]}
    )


def make_provider(
    geocoder: Handler = geocoder_ok, router: Handler = osrm_ok
) -> tuple[OsmRouteProvider, list[httpx.Request]]:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return geocoder(request) if request.url.host == "geo.test" else router(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OsmRouteProvider(client, GEOCODER, ROUTER, min_geocode_interval_s=0)
    return provider, calls


def test_haversine_warsaw_krakow() -> None:
    assert haversine_km(52.2297, 21.0122, 50.0647, 19.9450) == pytest.approx(252, abs=1)


def test_get_route_uses_osrm_distance_and_duration() -> None:
    provider, calls = make_provider()

    route = provider.get_route("Warszawa", "Kraków")

    assert route.source == "osrm"
    assert route.road_km == pytest.approx(293.4)
    assert route.driving_duration_min == pytest.approx(180)
    assert route.great_circle_km == pytest.approx(252, abs=1)
    assert (route.origin.name, route.destination.name) == ("Warszawa", "Kraków")
    osrm_request = calls[-1]
    assert osrm_request.url.path == "/route/v1/driving/21.0122,52.2297;19.945,50.0647"


@pytest.mark.parametrize(
    "router",
    [
        lambda _: httpx.Response(500),
        lambda _: httpx.Response(200, json={"code": "NoRoute", "routes": []}),
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("down", request=request)),
    ],
    ids=["http-500", "no-route", "connection-error"],
)
def test_falls_back_to_estimate_when_routing_fails(router: Handler) -> None:
    provider, _ = make_provider(router=router)

    route = provider.get_route("Warszawa", "Kraków")

    assert route.source == "estimate"
    assert route.driving_duration_min is None
    assert route.road_km == pytest.approx(route.great_circle_km * 1.25)


def test_unknown_place_raises_place_not_found() -> None:
    provider, _ = make_provider()

    with pytest.raises(PlaceNotFoundError) as exc_info:
        provider.get_route("Warszawa", "Atlantyda")

    assert exc_info.value.code == "UNKNOWN_PLACE"
    assert exc_info.value.details == {"place": "Atlantyda"}


@pytest.mark.parametrize(
    "geocoder",
    [
        lambda _: httpx.Response(503),
        lambda _: httpx.Response(200, text="<html>not json</html>"),
        lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request)),
    ],
    ids=["http-503", "invalid-json", "timeout"],
)
def test_geocoder_failure_raises_external_service_error(geocoder: Handler) -> None:
    provider, _ = make_provider(geocoder=geocoder)

    with pytest.raises(ExternalServiceError) as exc_info:
        provider.get_route("Warszawa", "Kraków")

    assert exc_info.value.code == "SERVICE_UNAVAILABLE"


def test_geocoding_results_are_cached() -> None:
    provider, calls = make_provider()

    provider.geocode("Warszawa")
    provider.geocode("  warszawa ")

    assert len([c for c in calls if c.url.host == "geo.test"]) == 1


def test_build_route_provider_uses_settings() -> None:
    settings = Settings(
        geocoder_url="https://geo.example/",
        http_user_agent="EcoRoute-test/1.0",
        http_timeout_s=3,
    )

    provider = build_route_provider(settings)

    assert provider._geocoder_url == "https://geo.example"
    assert provider._client.headers["User-Agent"] == "EcoRoute-test/1.0"
    assert provider._client.timeout.read == 3


def test_cache_evicts_least_recently_used() -> None:
    provider, calls = make_provider()
    provider._cache_size = 1

    provider.geocode("Warszawa")
    provider.geocode("Kraków")
    provider.geocode("Warszawa")

    assert len(calls) == 3
