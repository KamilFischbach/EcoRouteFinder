"""Trip parser: rule-based fallback (EN + PL) and the LLM path with a fake client."""

import json

import pytest

from app.ai.llm_client import LLMError
from app.ai.prompts import TRIP_PARSER_SYSTEM_V2
from app.ai.trip_parser import ParsedTrip, parse_trip, parse_trip_with_rules
from app.models.trip import TransportMode
from tests.fakes import FakeLLMClient, reply

M = TransportMode

# --- rules -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "origin", "destination"),
    [
        ("from Warsaw to Berlin tomorrow", "Warsaw", "Berlin"),
        ("Tomorrow we go from Nowy Sącz to Bielsko-Biała", "Nowy Sącz", "Bielsko-Biała"),
        ("Gdańsk to Sopot by bike", "Gdańsk", "Sopot"),
        ("Kraków → Zakopane", "Kraków", "Zakopane"),
        ("Poznań -> Wrocław, 2 people", "Poznań", "Wrocław"),
        ("jutro jadę z Gdyni do Torunia z żoną", "Gdyni", "Torunia"),
        ("Ze Szczecina do Gdańska pociągiem", "Szczecina", "Gdańska"),
        ("Weekend in Warsaw from Gdynia, 4 friends, fast", "Gdynia", "Warsaw"),
        ("Ski trip Tczew → Karpacz for 2 with equipment", "Tczew", "Karpacz"),
    ],
)
def test_rules_find_route(text: str, origin: str, destination: str) -> None:
    draft = parse_trip_with_rules(text)

    assert (draft.origin, draft.destination) == (origin, destination)
    assert draft.parsed_by == "rules"


@pytest.mark.parametrize(
    ("text", "passengers"),
    [
        ("3 people from A to B", 3),
        ("we are 4", 4),
        ("We're five", 5),
        ("three travellers", 3),
        ("with my wife", 2),
        ("going alone", 1),
        ("2 osoby", 2),
        ("pięć osób", 5),
        ("jest nas 6", 6),
        ("jedziemy we troje", 3),
        ("z kolegą", 2),
        ("jadę sama", 1),
        ("Cheapest way, solo", 1),
        ("4 friends, fast", 4),
        ("with 3 friends", 4),
        ("ski trip for 2 with equipment", 2),
        ("with my girlfriend", 2),
        ("staying for 3 nights", None),
        ("12 people", None),  # out of range
        ("from A to B", None),
    ],
)
def test_rules_find_passengers(text: str, passengers: int | None) -> None:
    assert parse_trip_with_rules(text).passengers == passengers


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("by train", M.TRAIN),
        ("pociągiem", M.TRAIN),
        ("we fly", M.PLANE),
        ("lecimy samolotem", M.PLANE),
        ("on my bike", M.BIKE),
        ("rowerem", M.BIKE),
        ("by coach", M.COACH),
        ("autobusem", M.COACH),
        ("by car", M.CAR_PETROL),
        ("samochodem", M.CAR_PETROL),
        ("in my EV", M.CAR_EV),
        ("electric car", M.CAR_EV),
        ("elektrykiem", M.CAR_EV),
        ("train or car?", None),  # ambiguous
        ("no idea yet", None),
    ],
)
def test_rules_find_mode(text: str, mode: TransportMode | None) -> None:
    assert parse_trip_with_rules(text).mode == mode


SKI_TEXT = (
    "I want to go skiing with my girlfriend from Tczew to Karpacz. "
    "We have ski equipment and comfort matters to us."
)


@pytest.mark.parametrize(
    ("text", "preferences"),
    [
        (
            SKI_TEXT,
            "I want to go skiing with my girlfriend; "
            "We have ski equipment and comfort matters to us",
        ),
        ("Ski trip Tczew → Karpacz for 2 with equipment", "Ski trip for 2 with equipment"),
        ("Cheapest way from Gdańsk to Kraków, solo", "Cheapest way"),
        ("Weekend in Warsaw from Gdynia, 4 friends, fast", "fast"),
        (
            "Jedziemy z Tczewa do Karpacza na narty. Mamy sprzęt i zależy nam na wygodzie.",
            "Jedziemy na narty; Mamy sprzęt i zależy nam na wygodzie",
        ),
        (
            "z Gdyni do Torunia z żoną, mamy dużą walizkę, chcemy tanio",
            "mamy dużą walizkę; chcemy tanio",
        ),
        ("jadę z psem z Gdyni do Torunia, szybko", "jadę z psem; szybko"),
    ],
)
def test_rules_find_preferences(text: str, preferences: str) -> None:
    assert parse_trip_with_rules(text).preferences == preferences


@pytest.mark.parametrize(
    "text",
    [
        "from Warsaw to Berlin tomorrow",
        "jutro jadę z Gdyni do Torunia z żoną",
        "Breakfast in Gdańsk, then we are asking for directions",  # no "fast", no "ski"
        "Trip from Polski Zakątek to Kraków",
    ],
)
def test_rules_return_no_preferences_when_none_are_mentioned(text: str) -> None:
    assert parse_trip_with_rules(text).preferences is None


def test_rules_parse_the_ski_example_in_full() -> None:
    draft = parse_trip_with_rules(SKI_TEXT)

    assert (draft.origin, draft.destination, draft.passengers) == ("Tczew", "Karpacz", 2)
    assert draft.mode is None
    assert draft.missing_fields == []


def test_rules_full_polish_sentence() -> None:
    draft = parse_trip_with_rules("Jutro jadę z Gdyni do Torunia z żoną pociągiem")

    assert draft.origin == "Gdyni"
    assert draft.destination == "Torunia"
    assert draft.passengers == 2
    assert draft.mode is M.TRAIN
    assert draft.missing_fields == []


def test_rules_report_missing_fields_when_nothing_is_found() -> None:
    draft = parse_trip_with_rules("I want to travel somewhere nice")

    assert (draft.origin, draft.destination, draft.passengers, draft.mode) == (None,) * 4
    assert draft.preferences is None
    assert draft.missing_fields == ["origin", "destination", "passengers"]


# --- LLM path ----------------------------------------------------------------------

TEXT = "jutro jadę z Gdyni do Torunia z żoną"
GOOD = {
    "origin": "Gdynia",
    "destination": "Toruń",
    "passengers": 2,
    "mode": None,
    "preferences": None,
}


def llm_answer(**overrides: object) -> str:
    return json.dumps({**GOOD, **overrides})


def test_llm_result_is_used_when_valid() -> None:
    client = FakeLLMClient([reply(json.dumps(GOOD))])

    draft = parse_trip(TEXT, client)

    assert draft.parsed_by == "llm"
    assert (draft.origin, draft.destination, draft.passengers) == ("Gdynia", "Toruń", 2)
    assert draft.preferences is None
    request = client.requests[0]
    assert request["response_schema"] == ParsedTrip.model_json_schema()
    assert request["messages"][0] == {"role": "system", "content": TRIP_PARSER_SYSTEM_V2}
    assert TEXT in request["messages"][1]["content"]


def test_llm_missing_fields_are_reported() -> None:
    client = FakeLLMClient(
        [reply(llm_answer(origin=None, destination="Zakopane", passengers=None))]
    )

    draft = parse_trip("weekend w Zakopanem", client)

    assert draft.parsed_by == "llm"
    assert draft.missing_fields == ["origin", "passengers"]


def test_llm_preferences_are_returned() -> None:
    answer = llm_answer(
        origin="Tczew", destination="Karpacz", preferences="ski equipment, comfort matters"
    )

    draft = parse_trip(SKI_TEXT, FakeLLMClient([reply(answer)]))

    assert draft.parsed_by == "llm"
    assert draft.preferences == "ski equipment, comfort matters"
    assert draft.mode is None


def test_llm_blank_preferences_become_null() -> None:
    draft = parse_trip(TEXT, FakeLLMClient([reply(llm_answer(preferences="  "))]))

    assert draft.parsed_by == "llm"
    assert draft.preferences is None


def test_llm_preferences_with_an_invented_number_are_replaced_by_rules() -> None:
    text = "z Gdyni do Torunia z żoną, mamy walizki"
    client = FakeLLMClient([reply(llm_answer(preferences="3 suitcases, budget under 100 PLN"))])

    draft = parse_trip(text, client)

    assert draft.parsed_by == "llm"  # the route is still the model's
    assert draft.origin == "Gdynia"
    assert draft.preferences == "mamy walizki"


def test_llm_preferences_may_repeat_numbers_from_the_text() -> None:
    text = "z Gdyni do Torunia z żoną, mamy 2 walizki"
    client = FakeLLMClient([reply(llm_answer(preferences="2 suitcases"))])

    assert parse_trip(text, client).preferences == "2 suitcases"


@pytest.mark.parametrize(
    "content",
    [
        "Sure! Gdynia to Toruń.",  # not JSON
        llm_answer(passengers=20),
        llm_answer(mode="rocket"),
        '{"origin": "Gdynia", "destination": "Toruń"}',  # missing keys
        '{"origin": "Gdynia", "destination": "Toruń", "passengers": 2, "mode": null}',
        llm_answer(x=1),
        llm_answer(origin="Gdańsk"),  # invented
        llm_answer(preferences="x" * 301),
    ],
    ids=[
        "not-json",
        "too-many-passengers",
        "bad-mode",
        "missing-keys",
        "missing-preferences",
        "extra-key",
        "invented",
        "preferences-too-long",
    ],
)
def test_bad_llm_output_falls_back_to_rules(content: str) -> None:
    draft = parse_trip(TEXT, FakeLLMClient([reply(content)]))

    assert draft.parsed_by == "rules"
    assert (draft.origin, draft.destination, draft.passengers) == ("Gdyni", "Torunia", 2)


def test_llm_error_falls_back_to_rules() -> None:
    draft = parse_trip(TEXT, FakeLLMClient([LLMError("timeout")]))

    assert draft.parsed_by == "rules"


def test_offline_llm_is_not_called() -> None:
    client = FakeLLMClient([reply(json.dumps(GOOD))], available=False)

    draft = parse_trip(TEXT, client)

    assert draft.parsed_by == "rules"
    assert client.requests == []


def test_no_client_uses_rules() -> None:
    assert parse_trip(TEXT, None).parsed_by == "rules"
