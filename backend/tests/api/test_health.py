from fastapi.testclient import TestClient

from tests.conftest import LLMSlot
from tests.fakes import FakeLLMClient


def test_health_without_ai(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ai_available": False, "ai_model": None}


def test_health_reports_available_model(client: TestClient, llm: LLMSlot) -> None:
    llm.client = FakeLLMClient(available=True, model="qwen2.5:7b")

    body = client.get("/api/v1/health").json()

    assert body == {"status": "ok", "ai_available": True, "ai_model": "qwen2.5:7b"}


def test_health_reports_offline_model(client: TestClient, llm: LLMSlot) -> None:
    llm.client = FakeLLMClient(available=False, model="qwen2.5:7b")

    body = client.get("/api/v1/health").json()

    assert body["ai_available"] is False
    assert body["ai_model"] == "qwen2.5:7b"


def test_unknown_route_uses_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
