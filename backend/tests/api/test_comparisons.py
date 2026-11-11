from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ExternalServiceError, PlaceNotFoundError
from tests.fakes import FakeRouteProvider, make_route

URL = "/api/v1/comparisons"


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"origin": "Warszawa", "destination": "Kraków", "passengers": 2}
    payload.update(overrides)
    return payload


def test_comparison_returns_route_options_and_highlights(
    client: TestClient, route_provider: FakeRouteProvider
) -> None:
    response = client.post(URL, json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["route"] == {
        "origin": {"name": "Warszawa", "lat": 52.2297, "lon": 21.0122},
        "destination": {"name": "Kraków", "lat": 50.0647, "lon": 19.945},
        "distance_km": 293.4,
        "source": "osrm",
    }
    assert body["passengers"] == 2
    assert len(body["options"]) == 6
    assert set(body["options"][0]) == {
        "mode",
        "distance_km",
        "duration_min",
        "cost_pln",
        "co2_kg",
        "co2_saved_vs_petrol_car_kg",
        "practical",
        "note",
    }
    assert body["highlights"] == {"greenest": "train", "fastest": "car_ev", "cheapest": "car_ev"}
    plane = next(o for o in body["options"] if o["mode"] == "plane")
    assert plane["practical"] is False
    assert plane["note"] == "Not worth flying under 300 km."
    assert route_provider.calls == [("Warszawa", "Kraków")]


def test_comparison_with_manual_distance_skips_routing(
    client: TestClient, route_provider: FakeRouteProvider
) -> None:
    response = client.post(URL, json=_payload(distance_km=15, passengers=1))

    assert response.status_code == 201
    body = response.json()
    assert body["route"]["source"] == "user"
    assert body["route"]["origin"] == {"name": "Warszawa", "lat": None, "lon": None}
    assert body["highlights"]["greenest"] == "bike"
    assert route_provider.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        _payload(origin=""),
        _payload(passengers=0),
        _payload(passengers=10),
        _payload(distance_km=0),
        _payload(extra="x"),
        {"origin": "Warszawa"},
    ],
)
def test_comparison_validation_returns_422(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_place_returns_422(client: TestClient, route_provider: FakeRouteProvider) -> None:
    route_provider.error = PlaceNotFoundError("Atlantyda")

    response = client.post(URL, json=_payload(destination="Atlantyda"))

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "UNKNOWN_PLACE",
        "message": "Could not find a place called 'Atlantyda'",
        "details": {"place": "Atlantyda"},
    }


def test_geocoder_down_returns_503(client: TestClient, route_provider: FakeRouteProvider) -> None:
    route_provider.error = ExternalServiceError("geocoding")

    response = client.post(URL, json=_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_same_place_returns_route_too_short(
    client: TestClient, route_provider: FakeRouteProvider
) -> None:
    route_provider.route = make_route(great_circle_km=0.0, road_km=0.0)

    response = client.post(URL, json=_payload(destination="Warszawa"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ROUTE_TOO_SHORT"


def test_comparison_keeps_a_planned_travel_date(client: TestClient) -> None:
    planned = (datetime.now(UTC) + timedelta(days=4)).date().isoformat()

    created = client.post(URL, json=_payload(travelled_on=planned)).json()

    assert created["travelled_on"] == planned
    assert client.get(f"{URL}/{created['id']}").json()["travelled_on"] == planned
    assert client.get(URL).json()[0]["travelled_on"] == planned


def test_comparison_travel_date_defaults_to_today(client: TestClient) -> None:
    created = client.post(URL, json=_payload()).json()

    assert created["travelled_on"] == datetime.now(UTC).date().isoformat()


def test_comparison_more_than_a_year_ahead_returns_422(client: TestClient) -> None:
    too_far = (datetime.now(UTC) + timedelta(days=400)).date().isoformat()

    response = client.post(URL, json=_payload(travelled_on=too_far))

    assert response.status_code == 422
