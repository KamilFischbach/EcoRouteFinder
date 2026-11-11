from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

TRIPS_URL = "/api/v1/trips"
MakePayload = Callable[..., dict[str, Any]]


def _create(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(TRIPS_URL, json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


# --- create -----------------------------------------------------------------


def test_create_trip_returns_201_with_body(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    response = client.post(TRIPS_URL, json=make_trip_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["origin"] == "Warszawa"
    assert body["mode"] == "train"
    # Train, per person: 340 km x 0.03092 kg/pkm.
    assert body["co2_kg"] == pytest.approx(10.51)
    assert body["created_at"].endswith("Z")


def test_create_trip_strips_text_and_blank_note(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    body = _create(client, make_trip_payload(origin="  Kraków ", note="   "))

    assert body["origin"] == "Kraków"
    assert body["note"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("distance_km", 0),
        ("distance_km", -5),
        ("passengers", 0),
        ("passengers", 10),
        ("mode", "rocket"),
        ("origin", ""),
    ],
)
def test_create_trip_invalid_returns_422(
    client: TestClient, make_trip_payload: MakePayload, field: str, value: Any
) -> None:
    response = client.post(TRIPS_URL, json=make_trip_payload(**{field: value}))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in error["details"]] == [field]


def test_create_trip_missing_fields_returns_422(client: TestClient) -> None:
    response = client.post(TRIPS_URL, json={})

    assert response.status_code == 422
    fields = {detail["field"] for detail in response.json()["error"]["details"]}
    assert fields == {"origin", "destination", "distance_km", "mode"}


def test_create_trip_defaults_travel_date_to_today(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    body = _create(client, make_trip_payload())

    assert body["travelled_on"] == datetime.now(UTC).date().isoformat()


def test_create_trip_keeps_a_past_travel_date(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    body = _create(client, make_trip_payload(travelled_on="2026-03-14"))

    assert body["travelled_on"] == "2026-03-14"


def test_create_trip_accepts_a_planned_date(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    planned = (datetime.now(UTC) + timedelta(days=5)).date().isoformat()

    body = _create(client, make_trip_payload(travelled_on=planned))

    assert body["travelled_on"] == planned


@pytest.mark.parametrize("days_ahead", [368, 5000])
def test_create_trip_more_than_a_year_ahead_returns_422(
    client: TestClient, make_trip_payload: MakePayload, days_ahead: int
) -> None:
    too_far = (datetime.now(UTC) + timedelta(days=days_ahead)).date().isoformat()

    response = client.post(TRIPS_URL, json=make_trip_payload(travelled_on=too_far))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_trip_more_than_a_year_ahead_returns_422(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    trip = _create(client, make_trip_payload())
    too_far = (datetime.now(UTC) + timedelta(days=400)).date().isoformat()

    response = client.put(f"{TRIPS_URL}/{trip['id']}", json={"travelled_on": too_far})

    assert response.status_code == 422


def test_update_trip_rejects_null_travel_date(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    trip = _create(client, make_trip_payload())

    response = client.put(f"{TRIPS_URL}/{trip['id']}", json={"travelled_on": None})

    assert response.status_code == 422


# --- read -------------------------------------------------------------------


def test_list_trips_returns_newest_first(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    first = _create(client, make_trip_payload(origin="A"))
    second = _create(client, make_trip_payload(origin="B"))

    response = client.get(TRIPS_URL)

    assert response.status_code == 200
    assert [trip["id"] for trip in response.json()] == [second["id"], first["id"]]


def test_list_trips_sorts_by_travel_date(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    older = _create(client, make_trip_payload(travelled_on="2026-05-01"))
    newer = _create(client, make_trip_payload(travelled_on="2026-06-01"))
    oldest = _create(client, make_trip_payload(travelled_on="2026-01-01"))

    response = client.get(TRIPS_URL)

    assert [t["id"] for t in response.json()] == [newer["id"], older["id"], oldest["id"]]


def test_list_trips_filters_by_mode(client: TestClient, make_trip_payload: MakePayload) -> None:
    _create(client, make_trip_payload(mode="train"))
    plane = _create(client, make_trip_payload(mode="plane"))

    response = client.get(TRIPS_URL, params={"mode": "plane"})

    assert response.status_code == 200
    assert [trip["id"] for trip in response.json()] == [plane["id"]]


def test_list_trips_invalid_mode_returns_422(client: TestClient) -> None:
    response = client.get(TRIPS_URL, params={"mode": "rocket"})

    assert response.status_code == 422


def test_get_trip_returns_200(client: TestClient, make_trip_payload: MakePayload) -> None:
    created = _create(client, make_trip_payload())

    response = client.get(f"{TRIPS_URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_trip_returns_404(client: TestClient) -> None:
    response = client.get(f"{TRIPS_URL}/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Trip with id 999 not found",
            "details": {"resource": "Trip", "id": 999},
        }
    }


# --- update -----------------------------------------------------------------


def test_update_trip_changes_only_sent_fields(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    created = _create(client, make_trip_payload())

    response = client.put(f"{TRIPS_URL}/{created['id']}", json={"passengers": 4, "mode": "coach"})

    assert response.status_code == 200
    body = response.json()
    assert body["passengers"] == 4
    assert body["mode"] == "coach"
    assert body["origin"] == created["origin"]
    assert body["updated_at"] >= created["updated_at"]


def test_update_trip_recalculates_co2(client: TestClient, make_trip_payload: MakePayload) -> None:
    created = _create(client, make_trip_payload())

    response = client.put(
        f"{TRIPS_URL}/{created['id']}", json={"mode": "car_petrol", "distance_km": 100}
    )

    assert response.status_code == 200
    # Petrol car shared by 2 passengers: 100 km x 0.16152 kg/km / 2.
    assert response.json()["co2_kg"] == pytest.approx(8.08)


def test_update_trip_can_clear_note(client: TestClient, make_trip_payload: MakePayload) -> None:
    created = _create(client, make_trip_payload())

    response = client.put(f"{TRIPS_URL}/{created['id']}", json={"note": None})

    assert response.status_code == 200
    assert response.json()["note"] is None


@pytest.mark.parametrize(
    "payload",
    [{"distance_km": 0}, {"passengers": 12}, {"origin": None}, {"unknown": "x"}],
)
def test_update_trip_invalid_returns_422(
    client: TestClient, make_trip_payload: MakePayload, payload: dict[str, Any]
) -> None:
    created = _create(client, make_trip_payload())

    response = client.put(f"{TRIPS_URL}/{created['id']}", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_missing_trip_returns_404(client: TestClient) -> None:
    response = client.put(f"{TRIPS_URL}/999", json={"passengers": 2})

    assert response.status_code == 404


# --- delete -----------------------------------------------------------------


def test_delete_trip_returns_204_and_removes_it(
    client: TestClient, make_trip_payload: MakePayload
) -> None:
    created = _create(client, make_trip_payload())

    response = client.delete(f"{TRIPS_URL}/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"{TRIPS_URL}/{created['id']}").status_code == 404


def test_delete_missing_trip_returns_404(client: TestClient) -> None:
    response = client.delete(f"{TRIPS_URL}/999")

    assert response.status_code == 404
