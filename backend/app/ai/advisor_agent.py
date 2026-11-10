"""Tool-calling advisor agent.

Loop (TODO):
1. Send `prompts.ADVISOR_SYSTEM_V1` + user question + `ADVISOR_TOOLS` to the `LLMClient`.
2. For each requested tool call, run the matching deterministic function
   (services.emissions / services.routing / services.weather) and send the result back.
3. Stop after a final answer or `MAX_STEPS` iterations.
4. Fallback when the LLM is unavailable: compute the comparison with services directly and
   return a templated recommendation (no LLM involved).
"""

from dataclasses import dataclass

from app.ai.llm_client import LLMClient, ToolSpec

MAX_STEPS = 5

# TODO: fill in JSON-schema parameters for each tool.
ADVISOR_TOOLS: list[ToolSpec] = [
    {
        "name": "calculate_emissions",
        "description": "Return kg CO2 for a distance, transport mode and passenger count.",
        "parameters": {},
    },
    {
        "name": "get_weather",
        "description": "Return current weather for a location.",
        "parameters": {},
    },
    {
        "name": "get_route",
        "description": "Return distance (km) and duration (min) between two places.",
        "parameters": {},
    },
]


@dataclass(frozen=True)
class AdvisorAnswer:
    text: str
    used_llm: bool


class AdvisorAgent:
    def __init__(self, client: LLMClient | None) -> None:
        self._client = client

    def ask(self, question: str) -> AdvisorAnswer:
        """Answer a travel question using tools. Not implemented yet."""
        raise NotImplementedError("TODO: tool-calling loop with fallback")
