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
        "missing_fields": [],
        "parsed_by": "rules",
    }


def test_draft_from_llm(client: TestClient, llm: LLMSlot) -> None:
    answer = {"origin": "Gdynia", "destination": "Toruń", "passengers": None, "mode": None}
    llm.client = FakeLLMClient([reply(json.dumps(answer))])

    body = client.post(URL, json={"text": "z Gdyni do Torunia"}).json()

    assert body["parsed_by"] == "llm"
    assert body["origin"] == "Gdynia"
    assert body["missing_fields"] == ["passengers"]


def test_draft_falls_back_when_llm_output_is_bad(client: TestClient, llm: LLMSlot) -> None:
    llm.client = FakeLLMClient([reply("not json")])

    body = client.post(URL, json={"text": "z Gdyni do Torunia"}).json()

    assert body["parsed_by"] == "rules"
    assert body["origin"] == "Gdyni"


@pytest.mark.parametrize(
    "payload",
    [{"text": ""}, {"text": "   "}, {"text": "x" * 501}, {}, {"text": "a", "extra": 1}],
    ids=["empty", "blank", "too-long", "missing", "extra-field"],
)
def test_draft_validation_returns_422(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
