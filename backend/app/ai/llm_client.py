"""LLM client abstraction and the Ollama implementation.

All AI code depends on the `LLMClient` Protocol, never on a concrete provider, so that:
- tests use a fake client (no network, deterministic),
- the app keeps working with a rule-based fallback when Ollama is down.

Ollama `/api/chat` contract used here (checked against docs/api.md and a local 0.9.6 server):
- request: `model`, `messages`, `stream: false`, `options.temperature`, optional `tools`
  (`[{"type": "function", "function": {name, description, parameters}}]`) and `format`
  (a JSON schema for structured output),
- response: `message.content` and optional `message.tool_calls[].function.{name, arguments}`
  where `arguments` is a JSON object (no call ids),
- tool results go back as `{"role": "tool", "content": ..., "tool_name": ...}`.
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, Protocol, TypedDict

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

AVAILABILITY_TTL_S = 30.0
AVAILABILITY_TIMEOUT_S = 5.0


class LLMError(Exception):
    """Any failure talking to the LLM. Callers turn it into a rule-based fallback."""


class ToolCallPayload(TypedDict):
    function: dict[str, Any]


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: NotRequired[list[ToolCallPayload]]
    """Assistant messages that requested tools (sent back as-is in the next request)."""
    tool_name: NotRequired[str]
    """Tool messages: which tool produced this result."""


class ToolSpec(TypedDict):
    """JSON-schema description of a tool the model may call."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)

    def as_message(self) -> ChatMessage:
        """The assistant message to append to the conversation."""
        message: ChatMessage = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {"function": {"name": c.name, "arguments": c.arguments}} for c in self.tool_calls
            ]
        return message


def system_message(content: str) -> ChatMessage:
    return {"role": "system", "content": content}


def user_message(content: str) -> ChatMessage:
    return {"role": "user", "content": content}


def tool_message(tool_name: str, content: str) -> ChatMessage:
    return {"role": "tool", "content": content, "tool_name": tool_name}


class LLMClient(Protocol):
    model: str

    def is_available(self) -> bool:
        """Cheap health check used to decide between LLM and rule-based fallback."""
        ...

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Raises `LLMError` on any failure."""
        ...


def _normalise_model(name: str) -> str:
    """Ollama lists untagged models as `<name>:latest`."""
    return name if ":" in name else f"{name}:latest"


def _parse_tool_call(raw: Any) -> ToolCall:
    function = raw.get("function") if isinstance(raw, dict) else None
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        raise LLMError(f"Malformed tool call: {raw!r}")
    arguments = function.get("arguments") or {}
    if isinstance(arguments, str):  # some models/servers send a JSON string
        try:
            arguments = json.loads(arguments)
        except ValueError as exc:
            raise LLMError("Tool call arguments are not valid JSON") from exc
    if not isinstance(arguments, dict):
        raise LLMError("Tool call arguments must be an object")
    return ToolCall(name=function["name"], arguments=arguments)


class OllamaClient:
    def __init__(
        self,
        http: httpx.Client,
        model: str,
        temperature: float = 0.2,
        availability_ttl_s: float = AVAILABILITY_TTL_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http = http
        self.model = model
        self._temperature = temperature
        self._ttl_s = availability_ttl_s
        self._clock = clock
        self._available: tuple[bool, float] | None = None

    def is_available(self) -> bool:
        now = self._clock()
        if self._available is not None and now - self._available[1] < self._ttl_s:
            return self._available[0]
        available = self._check_model_pulled()
        self._available = (available, now)
        return available

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": spec} for spec in tools]
        if response_schema is not None:
            payload["format"] = response_schema
        try:
            response = self._http.post("/api/chat", json=payload)
            response.raise_for_status()
            message = response.json()["message"]
            content = message.get("content") or ""
            calls = [_parse_tool_call(raw) for raw in message.get("tool_calls") or []]
        except LLMError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            self._available = None  # re-check health next time
            logger.warning("Ollama chat failed: %s", exc)
            raise LLMError(f"Ollama chat failed: {exc}") from exc
        return LLMResponse(content=content.strip(), tool_calls=calls)

    def _check_model_pulled(self) -> bool:
        try:
            response = self._http.get("/api/tags", timeout=AVAILABILITY_TIMEOUT_S)
            response.raise_for_status()
            models = response.json().get("models", [])
            names = {_normalise_model(str(m.get("name") or m.get("model"))) for m in models}
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            logger.info("Ollama not available: %s", exc)
            return False
        return _normalise_model(self.model) in names


def build_llm_client(settings: Settings) -> OllamaClient | None:
    """None when AI is disabled; callers then always use the rule-based fallback."""
    if not settings.ai_enabled:
        return None
    http = httpx.Client(
        base_url=settings.ollama_host.rstrip("/"),
        timeout=httpx.Timeout(settings.ollama_timeout_s, connect=5.0),
    )
    return OllamaClient(http, settings.ollama_model, settings.ollama_temperature)


@dataclass(frozen=True)
class AiStatus:
    available: bool
    model: str | None


def ai_status(client: LLMClient | None) -> AiStatus:
    if client is None:
        return AiStatus(available=False, model=None)
    return AiStatus(available=client.is_available(), model=client.model)
