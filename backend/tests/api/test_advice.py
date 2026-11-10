"""POST /comparisons/{id}/advice: always 200 (LLM or fallback), stored with the comparison."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import LLMSlot
from tests.fakes import FakeLLMClient, FakeWeather, call_tool, make_weather, reply

URL = "/api/v1/comparisons"


def _create(client: TestClient, **overrides: Any) -> int:
    payload = {"origin": "Warszawa", "destination": "Kraków", "passengers": 2, **overrides}
    response = client.post(URL, json=payload)
    assert response.status_code == 201
    comparison_id: int = response.json()["id"]
    return comparison_id


def test_rule_based_advice_without_ai(client: TestClient) -> None:
    comparison_id = _create(client)

    response = client.post(f"{URL}/{comparison_id}/advice")

    assert response.status_code == 200
    body = response.json()
    assert body["recommended_mode"] == "train"
    assert body["used_llm"] is False
    assert body["model"] is None
    assert body["preferences"] is None
    assert body["tool_trace"] == []
    assert body["weather"]["location"] == "Kraków"
    assert body["summary"].startswith("Train has the lowest CO₂")
    assert body["created_at"].endswith("Z")


def test_llm_advice_is_returned_and_stored(client: TestClient, llm: LLMSlot) -> None:
    comparison_id = _create(client)
    final = {"recommended_mode": "coach", "summary": "Coach is cheap and green.", "reasons": ["a"]}
    llm.client = FakeLLMClient(
        [
            call_tool("get_weather", location="Kraków"),
            reply("Dry weather."),
            reply(json.dumps(final)),
        ],
        model="qwen2.5:7b",
    )

    advice = client.post(f"{URL}/{comparison_id}/advice", json={"preferences": "cheap"}).json()

    assert advice["used_llm"] is True
    assert advice["model"] == "qwen2.5:7b"
    assert advice["recommended_mode"] == "coach"
    assert advice["preferences"] == "cheap"
    assert advice["tool_trace"] == [
        {"tool": "get_weather", "arguments": {"location": "Kraków"}, "ok": True}
    ]
    stored = client.get(f"{URL}/{comparison_id}").json()["advice"]
    assert stored == advice
    summary = client.get(URL).json()[0]
    assert summary["recommended_mode"] == "coach"


def test_failing_llm_still_returns_200(client: TestClient, llm: LLMSlot) -> None:
    comparison_id = _create(client)
    llm.client = FakeLLMClient([reply("not json"), reply("still not json")])

    response = client.post(f"{URL}/{comparison_id}/advice")

    assert response.status_code == 200
    assert response.json()["used_llm"] is False


def test_rain_keeps_the_bike_out(client: TestClient, weather: FakeWeather) -> None:
    weather.weather = make_weather(precipitation_mm=2.0, weather_code=63)
    comparison_id = _create(client, distance_km=10, passengers=1)

    body = client.post(f"{URL}/{comparison_id}/advice").json()

    assert body["recommended_mode"] != "bike"
    assert any("Bike skipped" in reason for reason in body["reasons"])


def test_new_advice_replaces_the_old_one(client: TestClient) -> None:
    comparison_id = _create(client)
    client.post(f"{URL}/{comparison_id}/advice")

    second = client.post(f"{URL}/{comparison_id}/advice", json={"preferences": "fastest"}).json()

    assert client.get(f"{URL}/{comparison_id}").json()["advice"] == second


def test_unknown_comparison_returns_404(client: TestClient) -> None:
    response = client.post(f"{URL}/999/advice")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "payload", [{"preferences": "x" * 301}, {"preferences": 5}, {"other": "x"}]
)
def test_invalid_preferences_return_422(client: TestClient, payload: dict[str, Any]) -> None:
    comparison_id = _create(client)

    response = client.post(f"{URL}/{comparison_id}/advice", json=payload)

    assert response.status_code == 422
