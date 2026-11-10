"""LLM client abstraction.

All AI code depends on the `LLMClient` Protocol, never on a concrete provider, so that:
- tests use a fake client (no network, deterministic),
- the app keeps working with a rule-based fallback when Ollama is down.

TODO:
- Implement `OllamaClient` on top of Ollama's `/api/chat` (httpx, timeouts, retries).
- `response_schema` -> Ollama `format` (JSON schema structured output).
- `tools` -> Ollama tool calling; return requested tool calls in `LLMResponse.tool_calls`.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


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


class LLMClient(Protocol):
    def is_available(self) -> bool:
        """Cheap health check used to decide between LLM and rule-based fallback."""
        ...

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse: ...


class OllamaClient:
    """Sketch of the Ollama implementation of `LLMClient`."""

    def __init__(self, host: str, model: str, timeout_s: float = 30.0) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def is_available(self) -> bool:
        # TODO: GET {host}/api/tags and check that `model` is pulled.
        return False

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        # TODO: POST {host}/api/chat with stream=false, format=response_schema, tools=tools.
        raise NotImplementedError("TODO: Ollama chat")
