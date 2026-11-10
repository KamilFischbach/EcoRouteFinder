"""EcoAdvisor: a tool-calling agent with a rule-based fallback.

LLM path:
1. System prompt `ADVISOR_SYSTEM_V4` + the stored comparison, destination weather and the
   user's preferences as context. Next to raw values the context carries ready-to-quote
   strings ("5 h 54 min", "152 PLN", "15.7 kg") from `services/formatting.py`, and the prompts
   tell the model to copy them verbatim.
2. Tool loop (at most `MAX_STEPS` rounds): run each requested tool from the registry and send
   the result back as a `tool` message.
3. A separate final call with `FinalAdvice`'s JSON schema as structured output (no tools). The
   model returns only the recommended mode and a short summary.
4. Grounding check: the recommended mode must be a practical option of this comparison that
   the luggage, equipment, comfort and weather rules (`suitable_options`) did not skip.
5. Reasons (all numbers and cheapest/fastest/lowest-CO2 labels) are built from the data by
   `advice_facts.build_reasons`. The summary is checked against the data: a false superlative
   or comparative, or a number that isn't in the data, rejects the answer.

Any failure (no client, offline, LLMError, too many steps, invalid JSON, ungrounded pick,
summary that contradicts the data) -> `rule_based_advice`, which needs no LLM.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from app.ai.advice_facts import (
    CHEAP_WORDS,
    FAST_WORDS,
    MODE_LABELS,
    SummaryMismatchError,
    build_reasons,
    check_summary,
    co2_line,
    mentions,
    special_needs,
    suitable_options,
)
from app.ai.llm_client import (
    LLMClient,
    LLMError,
    system_message,
    tool_message,
    user_message,
)
from app.ai.prompts import ADVISOR_FINAL_V4, ADVISOR_SYSTEM_V4
from app.ai.tools import ToolRegistry, comparison_to_tool_data, weather_to_tool_data
from app.models.trip import TransportMode
from app.services.comparison_models import ComparisonResult
from app.services.formatting import format_co2, format_cost, format_duration
from app.services.weather import WeatherInfo, WeatherProvider

logger = logging.getLogger(__name__)

MAX_STEPS = 4


@dataclass(frozen=True)
class ToolTraceItem:
    tool: str
    arguments: dict[str, Any]
    ok: bool


@dataclass(frozen=True)
class AdvisorAnswer:
    recommended_mode: TransportMode
    summary: str
    reasons: list[str]
    used_llm: bool
    model: str | None
    weather: WeatherInfo | None
    preferences: str | None
    tool_trace: list[ToolTraceItem] = field(default_factory=list)


class FinalAdvice(BaseModel):
    """Structured output the LLM must produce in the final call. Reasons are not part of it:
    they are generated from the data."""

    model_config = ConfigDict(extra="ignore")

    recommended_mode: TransportMode
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class AdvisorError(Exception):
    """The LLM path did not produce a usable, grounded answer."""


# --- rule-based fallback --------------------------------------------------------------


def rule_based_advice(
    comparison: ComparisonResult,
    preferences: str | None,
    weather: WeatherInfo | None,
    trace: list[ToolTraceItem] | None = None,
) -> AdvisorAnswer:
    candidates = suitable_options(comparison, preferences, weather).options

    if mentions(preferences, CHEAP_WORDS):
        pick = min(candidates, key=lambda o: (o.cost_pln, o.co2_kg))
        summary = (
            f"{MODE_LABELS[pick.mode]} is the cheapest practical option: about "
            f"{format_cost(pick.cost_pln)} per person, with {format_co2(pick.co2_kg)} CO₂."
        )
    elif mentions(preferences, FAST_WORDS):
        pick = min(candidates, key=lambda o: (o.duration_min, o.co2_kg))
        summary = (
            f"{MODE_LABELS[pick.mode]} is the fastest practical option: about "
            f"{format_duration(pick.duration_min)}, with {format_co2(pick.co2_kg)} CO₂ per person."
        )
    else:
        pick = min(candidates, key=lambda o: (o.co2_kg, o.duration_min))
        needs = special_needs(preferences)
        claim = (
            f"is the lowest-CO₂ option that suits {needs}"
            if needs
            else "has the lowest CO₂ of the practical options"
        )
        summary = f"{MODE_LABELS[pick.mode]} {claim}: {co2_line(pick, comparison.passengers)}."

    return AdvisorAnswer(
        recommended_mode=pick.mode,
        summary=summary,
        reasons=build_reasons(pick.mode, comparison, preferences, weather),
        used_llm=False,
        model=None,
        weather=weather,
        preferences=preferences,
        tool_trace=list(trace or []),
    )


# --- agent ----------------------------------------------------------------------------


def build_context(
    comparison: ComparisonResult, weather: WeatherInfo | None, preferences: str | None
) -> str:
    context = {
        "trip": comparison_to_tool_data(comparison),
        "weather_at_destination": weather_to_tool_data(weather) if weather else "unavailable",
        "user_preferences": preferences or "none given",
    }
    return "Context (JSON):\n" + json.dumps(context, ensure_ascii=False, indent=1)


class AdvisorAgent:
    def __init__(
        self,
        client: LLMClient | None,
        tools: ToolRegistry,
        weather: WeatherProvider,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self._client = client
        self._tools = tools
        self._weather = weather
        self._max_steps = max_steps

    def advise(self, comparison: ComparisonResult, preferences: str | None = None) -> AdvisorAnswer:
        weather = self._destination_weather(comparison)
        trace: list[ToolTraceItem] = []
        client = self._client
        if client is not None and client.is_available():
            try:
                final, reasons = self._ask_llm(client, comparison, preferences, weather, trace)
                return AdvisorAnswer(
                    recommended_mode=final.recommended_mode,
                    summary=final.summary,
                    reasons=reasons,
                    used_llm=True,
                    model=client.model,
                    weather=weather,
                    preferences=preferences,
                    tool_trace=trace,
                )
            except (LLMError, AdvisorError, SummaryMismatchError, ValidationError) as exc:
                logger.info("Advisor LLM path failed, using rules: %s", exc)
        return rule_based_advice(comparison, preferences, weather, trace)

    def _destination_weather(self, comparison: ComparisonResult) -> WeatherInfo | None:
        destination = comparison.route.destination
        if destination.lat is not None and destination.lon is not None:
            return self._weather.current(destination.lat, destination.lon, destination.name)
        return self._weather.for_place(destination.name)

    def _ask_llm(
        self,
        client: LLMClient,
        comparison: ComparisonResult,
        preferences: str | None,
        weather: WeatherInfo | None,
        trace: list[ToolTraceItem],
    ) -> tuple[FinalAdvice, list[str]]:
        tool_data: list[Any] = []  # what the model saw from tools; its numbers are allowed
        messages = [
            system_message(ADVISOR_SYSTEM_V4),
            user_message(build_context(comparison, weather, preferences)),
        ]
        for _ in range(self._max_steps):
            response = client.chat(messages, tools=self._tools.specs())
            messages.append(response.as_message())
            if not response.tool_calls:
                break
            for call in response.tool_calls:
                result = self._tools.run(call.name, call.arguments)
                trace.append(ToolTraceItem(result.name, result.arguments, result.ok))
                tool_data.append({"arguments": result.arguments, "result": result.data})
                messages.append(
                    tool_message(call.name, json.dumps(result.data, ensure_ascii=False))
                )
        else:
            raise AdvisorError(f"Still calling tools after {self._max_steps} steps")

        messages.append(user_message(ADVISOR_FINAL_V4))
        final_response = client.chat(messages, response_schema=FinalAdvice.model_json_schema())
        final = FinalAdvice.model_validate_json(final_response.content)

        check_grounding(final.recommended_mode, comparison, preferences, weather)
        reasons = build_reasons(final.recommended_mode, comparison, preferences, weather)
        check_summary(
            final.summary,
            final.recommended_mode,
            comparison,
            preferences,
            weather,
            reasons,
            tool_data,
        )
        return final, reasons


def check_grounding(
    mode: TransportMode,
    comparison: ComparisonResult,
    preferences: str | None,
    weather: WeatherInfo | None,
) -> None:
    """Reject picks the data rules out. Raises AdvisorError."""
    practical = {o.mode for o in comparison.options if o.practical}
    if mode not in practical:
        raise AdvisorError(f"Recommended {mode} is not a practical option")
    suitable = suitable_options(comparison, preferences, weather)
    if mode not in {o.mode for o in suitable.options}:
        raise AdvisorError(f"Recommended {mode} although: {' '.join(suitable.notes)}")
