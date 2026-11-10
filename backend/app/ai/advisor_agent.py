"""EcoAdvisor: a tool-calling agent with a rule-based fallback.

LLM path:
1. System prompt `ADVISOR_SYSTEM_V2` + the stored comparison, destination weather and the
   user's preferences as context.
2. Tool loop (at most `MAX_STEPS` rounds): run each requested tool from the registry and send
   the result back as a `tool` message.
3. A separate final call with `FinalAdvice`'s JSON schema as structured output (no tools).
4. Grounding check: the recommended mode must be a practical option of this comparison.

Any failure (no client, offline, LLMError, too many steps, invalid JSON, ungrounded pick) ->
`rule_based_advice`, which needs no LLM. Numbers always come from services, never the model.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.ai.llm_client import (
    LLMClient,
    LLMError,
    system_message,
    tool_message,
    user_message,
)
from app.ai.prompts import ADVISOR_FINAL_V1, ADVISOR_SYSTEM_V2
from app.ai.tools import ToolRegistry, comparison_to_tool_data
from app.models.trip import TransportMode
from app.services.comparison_models import ComparedOption, ComparisonResult
from app.services.weather import WeatherInfo, WeatherProvider, bad_for_cycling

logger = logging.getLogger(__name__)

MAX_STEPS = 4

MODE_LABELS: dict[TransportMode, str] = {
    TransportMode.CAR_PETROL: "Petrol car",
    TransportMode.CAR_EV: "Electric car",
    TransportMode.TRAIN: "Train",
    TransportMode.COACH: "Coach",
    TransportMode.PLANE: "Plane",
    TransportMode.BIKE: "Bike",
}

# Preference keywords for the rule-based fallback (English + Polish stems).
CHEAP_WORDS = ("cheap", "budget", "low cost", "tani", "tanio", "najtan")
FAST_WORDS = ("fast", "quick", "hurry", "asap", "szybk", "najszyb")
LUGGAGE_WORDS = ("luggage", "suitcase", "bags", "baggage", "bagaż", "walizk")


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


Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]


class FinalAdvice(BaseModel):
    """Structured output the LLM must produce in the final call."""

    model_config = ConfigDict(extra="forbid")

    recommended_mode: TransportMode
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]
    reasons: Annotated[list[Reason], Field(min_length=1, max_length=5)]


class AdvisorError(Exception):
    """The LLM path did not produce a usable, grounded answer."""


# --- formatting helpers --------------------------------------------------------------


def _kg(value: float) -> str:
    return f"{value:.1f} kg"


def _duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{mins} min" if hours == 0 else f"{hours} h {mins:02d} min"


def _savings(option: ComparedOption) -> str:
    saved = option.co2_saved_vs_car_kg
    if abs(saved) < 0.05:
        return "the same as driving alone"
    return f"{_kg(abs(saved))} {'less' if saved > 0 else 'more'} than driving alone"


def _mentions(text: str | None, words: tuple[str, ...]) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in words)


# --- rule-based fallback --------------------------------------------------------------


def rule_based_advice(
    comparison: ComparisonResult,
    preferences: str | None,
    weather: WeatherInfo | None,
    trace: list[ToolTraceItem] | None = None,
) -> AdvisorAnswer:
    practical = [o for o in comparison.options if o.practical] or list(comparison.options)
    candidates, notes = list(practical), []

    if _mentions(preferences, LUGGAGE_WORDS):
        candidates = [o for o in candidates if o.mode is not TransportMode.BIKE]
        notes.append("Bike skipped because you mentioned luggage.")
    weather_problem = bad_for_cycling(weather) if weather else None
    if weather_problem and any(o.mode is TransportMode.BIKE for o in candidates):
        candidates = [o for o in candidates if o.mode is not TransportMode.BIKE]
        notes.append(f"Bike skipped because of {weather_problem}.")
    candidates = candidates or practical

    if _mentions(preferences, CHEAP_WORDS):
        pick = min(candidates, key=lambda o: (o.cost_pln, o.co2_kg))
        summary = (
            f"{MODE_LABELS[pick.mode]} is the cheapest practical option: about "
            f"{pick.cost_pln:.0f} PLN per person, with {_kg(pick.co2_kg)} CO₂."
        )
    elif _mentions(preferences, FAST_WORDS):
        pick = min(candidates, key=lambda o: (o.duration_min, o.co2_kg))
        summary = (
            f"{MODE_LABELS[pick.mode]} is the fastest practical option: about "
            f"{_duration(pick.duration_min)}, with {_kg(pick.co2_kg)} CO₂ per person."
        )
    else:
        pick = min(candidates, key=lambda o: (o.co2_kg, o.duration_min))
        summary = (
            f"{MODE_LABELS[pick.mode]} has the lowest CO₂ of the practical options: "
            f"{_kg(pick.co2_kg)} per person, {_savings(pick)}."
        )

    reasons = [
        f"{_kg(pick.co2_kg)} CO₂ per person, {_savings(pick)}.",
        f"About {_duration(pick.duration_min)} door to door, roughly "
        f"{pick.cost_pln:.0f} PLN per person.",
        *notes,
    ]
    if weather and not weather_problem:
        reasons.append(
            f"Weather in {weather.location}: {weather.temperature_c:.0f} °C, "
            f"{weather.description or 'no rain'}."
        )
    return AdvisorAnswer(
        recommended_mode=pick.mode,
        summary=summary,
        reasons=reasons,
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
        "weather_at_destination": asdict(weather) if weather else "unavailable",
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
                final = self._ask_llm(client, comparison, preferences, weather, trace)
                return AdvisorAnswer(
                    recommended_mode=final.recommended_mode,
                    summary=final.summary,
                    reasons=list(final.reasons),
                    used_llm=True,
                    model=client.model,
                    weather=weather,
                    preferences=preferences,
                    tool_trace=trace,
                )
            except (LLMError, AdvisorError, ValidationError) as exc:
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
    ) -> FinalAdvice:
        messages = [
            system_message(ADVISOR_SYSTEM_V2),
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
                messages.append(
                    tool_message(call.name, json.dumps(result.data, ensure_ascii=False))
                )
        else:
            raise AdvisorError(f"Still calling tools after {self._max_steps} steps")

        messages.append(user_message(ADVISOR_FINAL_V1))
        final_response = client.chat(messages, response_schema=FinalAdvice.model_json_schema())
        final = FinalAdvice.model_validate_json(final_response.content)

        check_grounding(final.recommended_mode, comparison, preferences, weather)
        return final


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
    if mode is TransportMode.BIKE:
        if _mentions(preferences, LUGGAGE_WORDS):
            raise AdvisorError("Recommended the bike although the user has luggage")
        if weather is not None and bad_for_cycling(weather):
            raise AdvisorError("Recommended the bike in bad weather")
