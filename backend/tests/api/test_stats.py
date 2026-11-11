from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

STATS_URL = "/api/v1/stats"
MakePayload = Callable[..., dict[str, Any]]


def test_stats_default_to_90_days(client: TestClient, make_trip_payload: MakePayload) -> None:
    today = datetime.now(UTC).date()
    week_ago = (today - timedelta(days=7)).isoformat()
    client.post("/api/v1/trips", json=make_trip_payload(travelled_on=week_ago))
    client.post("/api/v1/trips", json=make_trip_payload(mode="plane", travelled_on=week_ago))

    response = client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["range"] == "90d"
    assert body["granularity"] == "week"
    assert body["to"] == today.isoformat()
    assert body["from"] == (today - timedelta(days=89)).isoformat()
    assert body["totals"]["trips"] == 2
    assert body["totals"]["eco_points"] > 0
    assert {m["mode"] for m in body["by_mode"]} == {"train", "plane"}
    assert body["best_trip"]["mode"] == "train"
    assert body["previous_period"]["totals"]["trips"] == 0
    assert set(body["previous_period"]) == {
        "from",
        "to",
        "totals",
        "co2_change_kg",
        "saved_change_kg",
        "co2_change_pct",
        "saved_change_pct",
    }


def test_stats_for_all_time_use_months(client: TestClient) -> None:
    response = client.get(STATS_URL, params={"range": "all"})

    assert response.status_code == 200
    assert response.json()["granularity"] == "month"
    assert response.json()["previous_period"] is None


def test_stats_with_unknown_range_return_422(client: TestClient) -> None:
    response = client.get(STATS_URL, params={"range": "7d"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_stats_on_empty_database_are_zeros(client: TestClient) -> None:
    response = client.get(STATS_URL, params={"range": "30d"})

    assert response.status_code == 200
    body = response.json()
    assert body["totals"] == {
        "trips": 0,
        "distance_km": 0.0,
        "co2_kg": 0.0,
        "co2_saved_kg": 0.0,
        "km_not_driven": 0.0,
        "eco_points": 0,
    }
    assert body["level"] == {
        "name": "Seedling",
        "points": 0,
        "next_level_name": "Sprout",
        "next_level_at": 250,
        "points_to_next": 250,
        "progress": 0.0,
        "ladder": [
            {"name": "Seedling", "min_points": 0, "reached": True},
            {"name": "Sprout", "min_points": 250, "reached": False},
            {"name": "Sapling", "min_points": 1500, "reached": False},
            {"name": "Tree", "min_points": 4000, "reached": False},
            {"name": "Forest", "min_points": 8000, "reached": False},
        ],
    }
    assert len(body["timeline"]) >= 5
    assert body["best_trip"] is None
