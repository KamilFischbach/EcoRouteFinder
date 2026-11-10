"""Deterministic reasons and the check of the advisor's summary against the data."""

import pytest

from app.ai.advice_facts import (
    SummaryMismatchError,
    build_reasons,
    check_summary,
    find_false_claims,
    find_unknown_numbers,
    known_numbers,
)
from app.models.trip import TransportMode
from app.services.comparison_models import ComparisonResult
from app.services.comparison_service import ComparisonService
from tests.fakes import FakeRouteProvider, make_weather

M = TransportMode
RAIN = make_weather(precipitation_mm=1.4, weather_code=63)

# long trip, practical options (per person):
#   train 9.35 kg, 217 min, 90.72 PLN  | coach 11.58 kg, 266 min, 52.81 PLN
#   EV 16.58 kg, 180 min, 36.67 PLN    | petrol 23.69 kg, 180 min, 66.02 PLN
# not practical: plane (fastest overall), bike (cheapest and greenest overall)


def long_trip() -> ComparisonResult:
    return ComparisonService(FakeRouteProvider()).compute("Warszawa", "Kraków", passengers=2)


def short_trip() -> ComparisonResult:
    return ComparisonService(FakeRouteProvider()).compute("Home", "Work", 1, distance_km=12)


def claims(summary: str, mode: TransportMode) -> list[str]:
    return find_false_claims(summary, mode, long_trip(), None, make_weather())


# --- reasons --------------------------------------------------------------------------


def test_reasons_for_greenest_pick() -> None:
    reasons = build_reasons(M.TRAIN, long_trip(), None, make_weather())

    assert reasons == [
        "9.3 kg CO₂ per person, 14.3 kg less than going by petrol car together.",
        "About 3 h 37 min door to door, roughly 91 PLN per person.",
        "Lowest CO₂ of the practical options.",
        "Weather in Kraków: 15 °C, partly cloudy.",
    ]


def test_reasons_combine_ranks_and_count_ties() -> None:
    reasons = build_reasons(M.CAR_EV, long_trip(), None, None)

    assert "Fastest and cheapest of the practical options." in reasons  # ties with petrol on time


def test_reasons_say_when_the_pick_ignores_a_cost_preference() -> None:
    reasons = build_reasons(M.TRAIN, long_trip(), "najtaniej", None)

    assert "Not the cheapest: Electric car costs about 37 PLN per person." in reasons


def test_reasons_say_when_the_pick_ignores_a_speed_preference() -> None:
    reasons = build_reasons(M.COACH, long_trip(), "fast please", None)

    assert "Not the fastest: Electric car takes about 3 h." in reasons


def test_reasons_explain_skipped_bike_and_hide_weather_line_in_rain() -> None:
    reasons = build_reasons(M.TRAIN, short_trip(), None, RAIN)

    assert any(r.startswith("Bike skipped because of") for r in reasons)
    assert "Lowest CO₂ of the remaining options." in reasons
    assert not any(r.startswith("Weather in") for r in reasons)


def test_reasons_reject_a_mode_outside_the_comparison() -> None:
    trip = long_trip()
    trip.options.pop()  # drop the plane

    with pytest.raises(ValueError):
        build_reasons(M.PLANE, trip, None, None)


# --- claims ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("summary", "mode"),
    [
        ("Take the train, the greenest practical option.", M.TRAIN),
        ("It has the lowest CO2 of the options that make sense.", M.TRAIN),
        ("The electric car is the cheapest and the fastest.", M.TRAIN),  # subject is the EV
        ("Take the train. The car is quicker, but the train is greener.", M.TRAIN),
        ("The train is greener than the coach.", M.TRAIN),
        ("The coach is cheaper than the train.", M.TRAIN),
        ("The coach is one of the cheapest options.", M.COACH),  # 2nd of 4
        ("The train is not the cheapest, but it is the greenest.", M.TRAIN),
        ("Pociąg nie jest najtańszy.", M.TRAIN),
        ("The train is the most expensive.", M.COACH),
        ("The train isn't the fastest option.", M.TRAIN),
        ("The plane would be the fastest, but flying 252 km makes no sense.", M.TRAIN),
        ("Cycling is the cheapest, but too far.", M.TRAIN),  # true among all options
        ("The train emits far less than going by car.", M.TRAIN),  # no mode to compare with
        ("Pociąg to najbardziej ekologiczna opcja.", M.TRAIN),
        ("Pociąg jest bardziej ekologiczny od samochodu.", M.TRAIN),
        ("Najtańszy jest samochód elektryczny, ale pociąg jest najczystszy.", M.TRAIN),
        ("A lot greener than the alternatives.", M.TRAIN),
    ],
)
def test_true_claims_are_accepted(summary: str, mode: TransportMode) -> None:
    assert claims(summary, mode) == []


@pytest.mark.parametrize(
    ("summary", "mode"),
    [
        ("The train is the cheapest practical option.", M.TRAIN),
        ("The train is green and one of the cheapest options.", M.TRAIN),  # priciest of 4
        ("It is the fastest way there.", M.COACH),  # subject = the recommended mode
        ("The coach is the greenest choice.", M.TRAIN),
        ("The petrol car is the slowest.", M.TRAIN),
        ("The coach is the most expensive.", M.COACH),
        ("The coach is faster than the train.", M.COACH),
        ("The train is cheaper than the coach.", M.TRAIN),
        ("The electric car is greener than the train.", M.TRAIN),
        ("The EV is faster than the petrol car.", M.CAR_EV),  # a tie is not "faster"
        ("Pociąg jest najtańszy.", M.TRAIN),
        ("Nie: autobus jest najszybszy.", M.COACH),  # "nie" too far away to negate
    ],
)
def test_false_claims_are_found(summary: str, mode: TransportMode) -> None:
    assert claims(summary, mode) != []


def test_bike_claims_respect_the_luggage_rule() -> None:
    trip = short_trip()

    # The bike is cheapest overall, so this stays true even when it was skipped.
    assert find_false_claims("The bike is the cheapest.", M.TRAIN, trip, "luggage", None) == []
    # Without the bike, the coach is the cheapest remaining option.
    assert find_false_claims("Coach is the cheapest.", M.COACH, trip, "luggage", None) == []
    assert find_false_claims("Train is the cheapest.", M.TRAIN, trip, "luggage", None) != []


# --- numbers --------------------------------------------------------------------------


def known(preferences: str | None = None, tool_data: list[object] | None = None) -> list[float]:
    trip = long_trip()
    reasons = build_reasons(M.TRAIN, trip, preferences, make_weather())
    return known_numbers(trip, make_weather(), preferences, reasons, tool_data or [])


@pytest.mark.parametrize(
    "summary",
    [
        "The train emits 9.35 kg of CO2 per person.",
        "About 9.3 kg CO₂ and 3 h 37 min.",
        "Roughly 91 PLN, or 90,72 PLN to be exact.",
        "Save 14.3 kg compared with going by petrol car together.",
        "The coach takes 4 h 26 min and costs 53 PLN.",
        "It takes about 3.6 hours.",
        "Great for 2 people; it is 15 °C in Kraków.",
        "Model qwen3:8b says hi.",
        "No numbers at all.",
    ],
)
def test_known_numbers_are_accepted(summary: str) -> None:
    assert find_unknown_numbers(summary, known()) == []


@pytest.mark.parametrize(
    ("summary", "unknown"),
    [
        ("The train emits 4.2 kg of CO2.", ["4.2"]),
        ("That is 80% less than driving.", ["80"]),
        ("About 9.4 kg and 120 PLN.", ["120"]),  # 9.4 rounds 9.35 within its precision
        ("It takes 2 h 13 min.", ["13"]),
    ],
)
def test_unknown_numbers_are_found(summary: str, unknown: list[str]) -> None:
    assert find_unknown_numbers(summary, known()) == unknown


def test_numbers_from_preferences_and_tools_are_allowed() -> None:
    tool = {"arguments": {"passengers": 4}, "result": {"co2_kg_per_person": 9.28}}
    numbers = known("what if we were 4?", [tool])

    assert find_unknown_numbers("For 4 people: 9.28 kg each.", numbers) == []
    assert find_unknown_numbers("For 5 people.", numbers) == ["5"]


def test_check_summary_raises_on_claim_or_number() -> None:
    trip = long_trip()
    reasons = build_reasons(M.TRAIN, trip, None, None)

    check_summary("Take the train, the greenest option.", M.TRAIN, trip, None, None, reasons)
    with pytest.raises(SummaryMismatchError, match="False claim"):
        check_summary("The train is the cheapest.", M.TRAIN, trip, None, None, reasons)
    with pytest.raises(SummaryMismatchError, match="Numbers not in the data: 64"):
        check_summary("Only 64 kg of CO2.", M.TRAIN, trip, None, None, reasons)
