import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import LLMSlot
from tests.fakes import FakeLLMClient, reply

URL = "/api/v1/trip-drafts"


def test_draft_from_rules_without_ai(client: TestClient) -> None:
    response = client.post(URL, json={"text": "from Warsaw to Berlin, 3 people, by train"})

    assert response.status_code == 200
    assert response.json() == {
        "origin": "Warsaw",
        "destination": "Berlin",
        "passengers": 3,
        "mode": "train",
        "preferences": None,
        "missing_fields": [],
        "parsed_by": "rules",
    }


def test_draft_from_llm(client: TestClient, llm: LLMSlot) -> None:
    answer = {
        "origin": "Gdynia",
        "destination": "Toruń",
        "passengers": None,
        "mode": None,
        "preferences": "large suitcase",
    }
    llm.client = FakeLLMClient([reply(json.dumps(answer))])

    body = client.post(URL, json={"text": "z Gdyni do Torunia z dużą walizką"}).json()

    assert body["parsed_by"] == "llm"
    assert body["origin"] == "Gdynia"
    assert body["preferences"] == "large suitcase"
    assert body["missing_fields"] == ["passengers"]


def test_draft_falls_back_when_llm_output_is_bad(client: TestClient, llm: LLMSlot) -> None:
    llm.client = FakeLLMClient([reply("not json")])

    body = client.post(URL, json={"text": "z Gdyni do Torunia"}).json()

    assert body["parsed_by"] == "rules"
    assert body["origin"] == "Gdyni"


def test_draft_preferences_from_rules(client: TestClient) -> None:
    text = "from Tczew to Karpacz with my girlfriend. We have ski equipment."

    body = client.post(URL, json={"text": text}).json()

    assert body["parsed_by"] == "rules"
    assert body["passengers"] == 2
    assert body["preferences"] == "We have ski equipment"


@pytest.mark.parametrize(
    "payload",
    [{"text": ""}, {"text": "   "}, {"text": "x" * 501}, {}, {"text": "a", "extra": 1}],
    ids=["empty", "blank", "too-long", "missing", "extra-field"],
)
def test_draft_validation_returns_422(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
