"""OllamaClient against httpx.MockTransport (no Ollama needed)."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.ai.llm_client import (
    LLMError,
    LLMResponse,
    OllamaClient,
    ToolCall,
    build_llm_client,
    tool_message,
    user_message,
)
from app.core.config import Settings

Handler = Callable[[httpx.Request], httpx.Response]
TAGS_OK = {"models": [{"name": "qwen2.5:7b", "model": "qwen2.5:7b"}]}


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_client(
    handler: Handler, model: str = "qwen2.5:7b", clock: Clock | None = None
) -> tuple[OllamaClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.Client(base_url="http://ollama.test", transport=httpx.MockTransport(record))
    return OllamaClient(http, model, temperature=0.2, clock=clock or Clock()), seen


def chat_reply(message: dict[str, Any]) -> Handler:
    return lambda _: httpx.Response(200, json={"model": "qwen2.5:7b", "message": message})


def raise_error(error: type[httpx.TransportError]) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error("boom", request=request)

    return handler


# --- is_available ------------------------------------------------------------------


def test_available_when_model_is_pulled() -> None:
    client, seen = make_client(lambda _: httpx.Response(200, json=TAGS_OK))

    assert client.is_available() is True
    assert seen[0].url.path == "/api/tags"


def test_untagged_model_matches_latest() -> None:
    tags = {"models": [{"name": "llama3:latest"}]}
    client, _ = make_client(lambda _: httpx.Response(200, json=tags), model="llama3")

    assert client.is_available() is True


def test_not_available_when_model_is_not_pulled() -> None:
    tags = {"models": [{"name": "llama3.2:latest"}]}
    client, _ = make_client(lambda _: httpx.Response(200, json=tags))

    assert client.is_available() is False


@pytest.mark.parametrize(
    "handler",
    [
        raise_error(httpx.ConnectError),
        lambda _: httpx.Response(500),
        lambda _: httpx.Response(200, text="not json"),
    ],
    ids=["no-connection", "http-500", "bad-json"],
)
def test_not_available_on_errors(handler: Handler) -> None:
    client, _ = make_client(handler)

    assert client.is_available() is False


def test_availability_is_cached_for_30_seconds() -> None:
    clock = Clock()
    client, seen = make_client(lambda _: httpx.Response(200, json=TAGS_OK), clock=clock)

    client.is_available()
    clock.now = 29.0
    client.is_available()
    assert len(seen) == 1

    clock.now = 31.0
    client.is_available()
    assert len(seen) == 2


# --- chat --------------------------------------------------------------------------


def test_chat_returns_plain_text_and_sends_options() -> None:
    client, seen = make_client(chat_reply({"role": "assistant", "content": " Take the train. "}))

    response = client.chat([user_message("How should I travel?")])

    assert response == LLMResponse(content="Take the train.")
    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/api/chat"
    assert body["model"] == "qwen2.5:7b"
    assert body["stream"] is False
    assert body["options"] == {"temperature": 0.2}
    assert "tools" not in body and "format" not in body


def test_chat_sends_schema_as_format() -> None:
    schema = {"type": "object", "properties": {"origin": {"type": "string"}}}
    client, seen = make_client(chat_reply({"role": "assistant", "content": '{"origin": "Gdynia"}'}))

    response = client.chat([user_message("z Gdyni")], response_schema=schema)

    assert json.loads(seen[0].content)["format"] == schema
    assert json.loads(response.content) == {"origin": "Gdynia"}


def test_chat_sends_tools_and_parses_tool_calls() -> None:
    message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "get_weather", "arguments": {"location": "Gdańsk"}}}],
    }
    client, seen = make_client(chat_reply(message))
    spec = {"name": "get_weather", "description": "Weather", "parameters": {"type": "object"}}

    response = client.chat([user_message("weather?")], tools=[spec])

    assert json.loads(seen[0].content)["tools"] == [{"type": "function", "function": spec}]
    assert response.tool_calls == [ToolCall("get_weather", {"location": "Gdańsk"})]
    assert response.as_message() == message


def test_chat_accepts_string_arguments() -> None:
    message = {"content": "", "tool_calls": [{"function": {"name": "x", "arguments": '{"a": 1}'}}]}
    client, _ = make_client(chat_reply(message))

    assert client.chat([user_message("hi")]).tool_calls == [ToolCall("x", {"a": 1})]


def test_tool_result_message_uses_tool_name() -> None:
    assert tool_message("get_weather", "{}") == {
        "role": "tool",
        "content": "{}",
        "tool_name": "get_weather",
    }


@pytest.mark.parametrize(
    "handler",
    [
        raise_error(httpx.ReadTimeout),
        raise_error(httpx.ConnectError),
        lambda _: httpx.Response(404, json={"error": "model not found"}),
        lambda _: httpx.Response(200, text="<html>"),
        lambda _: httpx.Response(200, json={"done": True}),
        chat_reply({"content": "", "tool_calls": [{"function": {"arguments": {}}}]}),
        chat_reply({"content": "", "tool_calls": [{"function": {"name": "x", "arguments": "{"}}]}),
    ],
    ids=[
        "timeout",
        "no-connection",
        "http-404",
        "not-json",
        "no-message",
        "tool-without-name",
        "bad-tool-arguments",
    ],
)
def test_chat_failures_raise_llm_error(handler: Handler) -> None:
    client, _ = make_client(handler)

    with pytest.raises(LLMError):
        client.chat([user_message("hi")])


def test_chat_failure_resets_availability_cache() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=TAGS_OK)
        raise httpx.ConnectError("down", request=request)

    client, seen = make_client(handler)
    client.is_available()
    with pytest.raises(LLMError):
        client.chat([user_message("hi")])
    client.is_available()

    assert [r.url.path for r in seen] == ["/api/tags", "/api/chat", "/api/tags"]


# --- factory -----------------------------------------------------------------------


def test_factory_returns_none_when_ai_disabled() -> None:
    assert build_llm_client(Settings(ai_enabled=False)) is None


def test_factory_uses_settings() -> None:
    settings = Settings(
        ai_enabled=True,
        ollama_host="http://gpu-box:11434/",
        ollama_model="llama3.1:8b",
        ollama_timeout_s=42,
    )

    client = build_llm_client(settings)

    assert client is not None
    assert client.model == "llama3.1:8b"
    assert str(client._http.base_url) == "http://gpu-box:11434"
    assert client._http.timeout.read == 42
