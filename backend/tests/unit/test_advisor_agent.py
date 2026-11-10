"""AdvisorAgent with a scripted fake LLM: tool loop, grounding and summary checks, fallback."""

import json
from collections.abc import Callable

import pytest

from app.ai.advisor_agent import MAX_STEPS, AdvisorAgent, FinalAdvice, rule_based_advice
from app.ai.llm_client import LLMError, LLMResponse
from app.ai.prompts import ADVISOR_FINAL_V3, ADVISOR_SYSTEM_V4
from app.ai.tools import build_tool_registry
from app.models.trip import TransportMode
from app.services.comparison_models import ComparisonResult
from app.services.comparison_service import ComparisonService
from tests.fakes import (
    FakeLLMClient,
    FakeRouteProvider,
    FakeWeather,
    call_tool,
    make_weather,
    reply,
)

M = TransportMode
RAIN = make_weather(precipitation_mm=1.4, weather_code=63)


def final(mode: str = "train", **overrides: object) -> LLMResponse:
    body = {
        "recommended_mode": mode,
        "summary": f"Take the {mode.replace('_', ' ')}: it suits this trip well.",
    }
    body.update(overrides)
    return reply(json.dumps(body))


def long_trip() -> ComparisonResult:
    """Warszawa -> Kraków for 2: train is the greenest practical option; plane and bike aren't."""
    return ComparisonService(FakeRouteProvider()).compute("Warszawa", "Kraków", passengers=2)


def short_trip() -> ComparisonResult:
    """12 km, entered by hand (no coordinates): the bike is practical and the greenest."""
    return ComparisonService(FakeRouteProvider()).compute("Home", "Work", 1, distance_km=12)


def make_agent(
    client: FakeLLMClient | None, weather: FakeWeather | None = None
) -> tuple[AdvisorAgent, FakeWeather]:
    weather = weather or FakeWeather(make_weather())
    tools = build_tool_registry(ComparisonService(FakeRouteProvider()), weather)
    return AdvisorAgent(client, tools, weather), weather


# --- LLM path -------------------------------------------------------------------------


def test_tool_call_then_result_then_final_answer() -> None:
    client = FakeLLMClient(
        [
            call_tool("calculate_emissions", distance_km=300, mode="train", passengers=4),
            reply("With 4 people the train is still 9.3 kg each."),
            final("train"),
        ]
    )
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip(), "what if we were 4?")

    assert answer.used_llm is True
    assert answer.model == "fake:1b"
    assert answer.recommended_mode is M.TRAIN
    assert answer.summary == "Take the train: it suits this trip well."
    assert answer.reasons[0] == (
        "9.3 kg CO₂ per person, 14.3 kg less than going by petrol car together."
    )
    assert "Lowest CO₂ of the practical options." in answer.reasons
    assert [(t.tool, t.ok) for t in answer.tool_trace] == [("calculate_emissions", True)]

    first, second, last = client.requests
    assert first["messages"][0]["content"] == ADVISOR_SYSTEM_V4
    context = first["messages"][1]["content"]
    assert '"user_preferences": "what if we were 4?"' in context
    assert '"weather_at_destination"' in context
    # Ready-to-quote strings next to the raw values (train for 2 on 293.4 km).
    assert '"duration": "3 h 37 min"' in context
    assert '"cost": "91 PLN"' in context
    assert '"co2": "9.3 kg"' in context
    assert '"co2_saved_vs_petrol_car": "14.3 kg less"' in context
    assert '"temperature": "15 °C"' in context
    assert {t["name"] for t in first["tools"]} == {
        "compare_travel_options",
        "get_weather",
        "calculate_emissions",
    }
    tool_msg = second["messages"][-1]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_name"] == "calculate_emissions"
    tool_result = json.loads(tool_msg["content"])
    assert tool_result["co2_kg_per_person"] == pytest.approx(9.28)
    assert tool_result["quote"] == {"co2_per_person": "9.3 kg"}
    assert last["tools"] is None
    assert last["response_schema"] == FinalAdvice.model_json_schema()
    assert last["messages"][-1]["content"] == ADVISOR_FINAL_V3


def test_answer_without_tools() -> None:
    client = FakeLLMClient([reply("The train is greenest."), final("coach")])
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip())

    assert answer.used_llm is True
    assert answer.recommended_mode is M.COACH
    assert answer.tool_trace == []


def test_unknown_tool_is_reported_back_to_the_model() -> None:
    client = FakeLLMClient([call_tool("book_ticket", mode="train"), reply("Sorry."), final()])
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip())

    assert answer.used_llm is True
    assert [(t.tool, t.ok) for t in answer.tool_trace] == [("book_ticket", False)]
    error = json.loads(client.requests[1]["messages"][-1]["content"])["error"]
    assert "Unknown tool 'book_ticket'" in error


def test_invalid_tool_arguments_are_reported_back_to_the_model() -> None:
    client = FakeLLMClient(
        [call_tool("calculate_emissions", distance_km=-5, mode="rocket"), reply("Hm."), final()]
    )
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip())

    assert answer.used_llm is True
    assert answer.tool_trace[0].ok is False
    error = json.loads(client.requests[1]["messages"][-1]["content"])["error"]
    assert error.startswith("Invalid arguments")
    assert "distance_km" in error and "mode" in error


def test_too_many_steps_falls_back() -> None:
    loop = [call_tool("get_weather", location="Kraków") for _ in range(MAX_STEPS)]
    client = FakeLLMClient([*loop, final()])
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip())

    assert answer.used_llm is False
    assert len(client.requests) == MAX_STEPS  # no final call
    assert len(answer.tool_trace) == MAX_STEPS  # the attempt stays visible


def test_impractical_recommendation_falls_back() -> None:
    client = FakeLLMClient([reply("Fly!"), final("plane")])  # plane is impractical here
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip())

    assert answer.used_llm is False
    assert answer.recommended_mode is M.TRAIN


@pytest.mark.parametrize(
    "bad_final",
    [
        reply("Take the train, it's great."),
        reply('{"recommended_mode": "train"}'),
        reply('{"recommended_mode": "teleport", "summary": "x"}'),
        final(summary="  "),
    ],
    ids=["not-json", "missing-fields", "unknown-mode", "empty-summary"],
)
def test_bad_final_json_falls_back(bad_final: LLMResponse) -> None:
    agent, _ = make_agent(FakeLLMClient([reply("Thinking."), bad_final]))

    answer = agent.advise(long_trip())

    assert answer.used_llm is False
    assert answer.recommended_mode is M.TRAIN


def test_reasons_come_from_data_not_from_the_model() -> None:
    client = FakeLLMClient([reply("Hm."), final("coach", reasons=["Coach is free!"])])
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip())

    assert answer.used_llm is True
    assert "Coach is free!" not in answer.reasons
    assert answer.reasons[:2] == [
        "11.6 kg CO₂ per person, 12.1 kg less than going by petrol car together.",
        "About 4 h 26 min door to door, roughly 53 PLN per person.",
    ]


@pytest.mark.parametrize(
    ("mode", "summary"),
    [
        ("train", "The train is green and one of the cheapest options."),  # smoke test: priciest
        ("coach", "Take the coach, the fastest way there."),
        ("coach", "The coach is cheaper than the electric car."),
        ("coach", "Autobus jest najtańszą opcją."),
        ("coach", "Take the coach: it emits only 4.2 kg of CO2."),  # invented number
    ],
)
def test_summary_that_contradicts_the_data_falls_back(mode: str, summary: str) -> None:
    client = FakeLLMClient([reply("Hm."), final(mode, summary=summary)])
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip())

    assert answer.used_llm is False
    assert answer.recommended_mode is M.TRAIN
    assert answer.summary.startswith("Train has the lowest CO₂")


def test_summary_with_tool_numbers_is_accepted() -> None:
    client = FakeLLMClient(
        [
            call_tool("calculate_emissions", distance_km=300, mode="train", passengers=4),
            reply("Done."),
            final(summary="Take the train, the greenest option: 9.28 kg each even for 4 people."),
        ]
    )
    agent, _ = make_agent(client)

    answer = agent.advise(long_trip(), "what if we were 4?")

    assert answer.used_llm is True
    assert answer.summary.startswith("Take the train, the greenest option")


def test_llm_error_falls_back() -> None:
    agent, _ = make_agent(FakeLLMClient([LLMError("timeout")]))

    assert agent.advise(long_trip()).used_llm is False


def test_bike_in_rain_from_llm_is_rejected() -> None:
    client = FakeLLMClient([reply("Cycle!"), final("bike")])
    agent, _ = make_agent(client, FakeWeather(RAIN))

    answer = agent.advise(short_trip())

    assert answer.used_llm is False
    assert answer.recommended_mode is not M.BIKE


def test_bike_with_luggage_from_llm_is_rejected() -> None:
    agent, _ = make_agent(FakeLLMClient([reply("Cycle!"), final("bike")]))

    answer = agent.advise(short_trip(), "I have a big suitcase / luggage")

    assert answer.used_llm is False
    assert answer.recommended_mode is not M.BIKE


@pytest.mark.parametrize("preferences", ["ski equipment", "comfort matters to us"])
def test_coach_for_bulky_or_comfort_trip_from_llm_is_rejected(preferences: str) -> None:
    agent, _ = make_agent(FakeLLMClient([reply("Coach!"), final("coach")]))

    answer = agent.advise(long_trip(), preferences)

    assert answer.used_llm is False
    assert answer.recommended_mode is M.TRAIN


def test_train_for_ski_trip_from_llm_is_accepted() -> None:
    agent, _ = make_agent(FakeLLMClient([reply("Train."), final("train")]))

    answer = agent.advise(long_trip(), "ski equipment, comfort matters")

    assert answer.used_llm is True
    assert "Coach skipped: on a trip over 200 km the train is easier with bulky equipment." in (
        answer.reasons
    )


def test_no_client_uses_rules() -> None:
    agent, _ = make_agent(None)

    answer = agent.advise(long_trip())

    assert answer.used_llm is False
    assert answer.model is None
    assert answer.recommended_mode is M.TRAIN


def test_offline_client_is_not_called() -> None:
    client = FakeLLMClient([final()], available=False)
    agent, _ = make_agent(client)

    assert agent.advise(long_trip()).used_llm is False
    assert client.requests == []


def test_weather_uses_coordinates_or_geocodes_by_name() -> None:
    agent, weather = make_agent(None)

    with_coords = agent.advise(long_trip())
    by_name = agent.advise(short_trip())

    assert with_coords.weather is not None and with_coords.weather.location == "Kraków"
    assert by_name.weather is not None and by_name.weather.location == "Work"
    assert weather.lookups == ["Kraków", "Work"]


# --- rule-based fallback ----------------------------------------------------------------


def test_fallback_picks_greenest_practical_option() -> None:
    answer = rule_based_advice(long_trip(), None, make_weather())

    assert answer.recommended_mode is M.TRAIN
    assert answer.summary.startswith("Train has the lowest CO₂")
    assert "9.3 kg CO₂ per person" in answer.reasons[0]
    assert any(r.startswith("Weather in Kraków") for r in answer.reasons)


def test_fallback_skips_bike_in_rain() -> None:
    answer = rule_based_advice(short_trip(), None, RAIN)

    assert answer.recommended_mode is not M.BIKE
    assert answer.recommended_mode is M.TRAIN
    assert any("Bike skipped because of" in r and "rain" in r for r in answer.reasons)


def test_fallback_keeps_bike_in_good_weather() -> None:
    assert rule_based_advice(short_trip(), None, make_weather()).recommended_mode is M.BIKE


def test_fallback_keeps_bike_without_weather_data() -> None:
    assert rule_based_advice(short_trip(), None, None).recommended_mode is M.BIKE


def test_fallback_reasons_rank_within_remaining_options() -> None:
    answer = rule_based_advice(short_trip(), "I have luggage", make_weather())

    assert answer.recommended_mode is M.TRAIN
    assert "Bike skipped because you mentioned luggage." in answer.reasons
    assert "Lowest CO₂ of the remaining options." in answer.reasons


@pytest.mark.parametrize(
    ("trip", "preferences", "expected"),
    [
        (short_trip, "I have luggage", M.TRAIN),  # bike would be greenest
        (short_trip, "mam dużą walizkę", M.TRAIN),
        (long_trip, "cheapest please", M.CAR_EV),  # EV shared by 2 is cheapest
        (long_trip, "najtaniej", M.CAR_EV),
        (long_trip, "as fast as possible", M.CAR_EV),  # cars are fastest, EV greener
    ],
)
def test_fallback_respects_preferences(
    trip: Callable[[], ComparisonResult], preferences: str, expected: TransportMode
) -> None:
    answer = rule_based_advice(trip(), preferences, make_weather())

    assert answer.recommended_mode is expected
    assert answer.preferences == preferences


@pytest.mark.parametrize(
    ("preferences", "bike_note", "needs"),
    [
        ("ski equipment", "Bike skipped because you have bulky equipment.", "bulky equipment"),
        ("jedziemy na narty, mamy sprzęt", "Bike skipped because you have bulky equipment.", None),
        ("comfort matters to us", "Bike skipped because comfort matters to you.", None),
        ("zależy nam na wygodzie", "Bike skipped because comfort matters to you.", None),
    ],
)
def test_fallback_skips_bike_for_equipment_or_comfort(
    preferences: str, bike_note: str, needs: str | None
) -> None:
    answer = rule_based_advice(short_trip(), preferences, make_weather())

    assert answer.recommended_mode is M.TRAIN
    assert bike_note in answer.reasons
    assert not any(r.startswith("Coach skipped") for r in answer.reasons)  # only 12 km
    if needs:
        assert answer.summary.startswith(f"Train is the lowest-CO₂ option that suits {needs}:")


@pytest.mark.parametrize(
    ("preferences", "expected", "coach_note"),
    [
        # Coach (53 PLN) is cheaper than the train (91 PLN) but ranked behind it on 293 km.
        ("ski equipment, cheap", M.CAR_EV, "the train is easier with bulky equipment"),
        ("comfort matters", M.TRAIN, "the train is more comfortable"),
        ("ski equipment, comfort matters", M.TRAIN, "the train is easier with bulky equipment"),
    ],
)
def test_fallback_ranks_coach_behind_train_on_long_trips(
    preferences: str, expected: TransportMode, coach_note: str
) -> None:
    answer = rule_based_advice(long_trip(), preferences, make_weather())

    assert answer.recommended_mode is expected
    assert f"Coach skipped: on a trip over 200 km {coach_note}." in answer.reasons


def test_fallback_summary_names_both_needs() -> None:
    answer = rule_based_advice(long_trip(), "ski equipment, comfort matters", make_weather())

    assert answer.summary.startswith(
        "Train is the lowest-CO₂ option that suits bulky equipment and a comfortable trip:"
    )


def test_fallback_keeps_coach_without_comfort_or_equipment() -> None:
    answer = rule_based_advice(long_trip(), "I am asking for the usual", make_weather())

    assert not any(r.startswith("Coach skipped") for r in answer.reasons)
