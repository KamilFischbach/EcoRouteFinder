"""Saved comparisons: create (201), list, get, delete."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.fakes import FakeRouteProvider, make_route

URL = "/api/v1/comparisons"


def _create(client: TestClient, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"origin": "Warszawa", "destination": "Kraków", "passengers": 2}
    payload.update(overrides)
    response = client.post(URL, json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_create_returns_id_timestamp_and_no_advice(client: TestClient) -> None:
    body = _create(client)

    assert body["id"] > 0
    assert body["created_at"].endswith("Z")
    assert body["advice"] is None


def test_get_returns_the_stored_snapshot(client: TestClient) -> None:
    created = _create(client)

    response = client.get(f"{URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_does_not_recompute(client: TestClient, route_provider: FakeRouteProvider) -> None:
    created = _create(client)
    route_provider.route = make_route(road_km=999.0)

    body = client.get(f"{URL}/{created['id']}").json()

    assert body["route"]["distance_km"] == 293.4
    assert len(route_provider.calls) == 1


def test_list_returns_newest_first_with_summary_fields(client: TestClient) -> None:
    first = _create(client, destination="Kraków")
    second = _create(client, passengers=1, distance_km=12)

    response = client.get(URL)

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [second["id"], first["id"]]
    newest, oldest = rows
    assert newest == {
        "id": second["id"],
        "origin": "Warszawa",
        "destination": "Kraków",
        "passengers": 1,
        "distance_km": 12.0,
        "created_at": second["created_at"],
        "greenest_mode": "bike",
        "greenest_co2_kg": 0.0,
        # Petrol car, one person, 12 km x 0.16152.
        "solo_car_co2_kg": 1.94,
        "recommended_mode": None,
    }
    assert oldest["greenest_mode"] == "train"
    assert oldest["greenest_co2_kg"] == pytest.approx(9.35)
    assert oldest["solo_car_co2_kg"] == pytest.approx(47.39)


def test_list_paginates(client: TestClient) -> None:
    ids = [_create(client, passengers=n)["id"] for n in (1, 2, 3)]

    page = client.get(URL, params={"limit": 2, "offset": 1}).json()

    assert [row["id"] for row in page] == [ids[1], ids[0]]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_rejects_bad_pagination(client: TestClient, params: dict[str, int]) -> None:
    response = client.get(URL, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_is_empty_without_comparisons(client: TestClient) -> None:
    assert client.get(URL).json() == []


def test_get_missing_returns_404(client: TestClient) -> None:
    response = client.get(f"{URL}/999")

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"resource": "Comparison", "id": 999}


def test_delete_returns_204_and_removes_it(client: TestClient) -> None:
    created = _create(client)

    response = client.delete(f"{URL}/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"{URL}/{created['id']}").status_code == 404
    assert client.get(URL).json() == []


def test_delete_missing_returns_404(client: TestClient) -> None:
    assert client.delete(f"{URL}/999").status_code == 404


def test_failed_comparison_is_not_saved(
    client: TestClient, route_provider: FakeRouteProvider
) -> None:
    route_provider.route = make_route(great_circle_km=0.0, road_km=0.0)

    assert client.post(URL, json={"origin": "A", "destination": "A"}).status_code == 422
    assert client.get(URL).json() == []
