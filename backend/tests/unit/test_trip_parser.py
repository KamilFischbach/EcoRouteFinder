"""Trip parser: rule-based fallback (EN + PL) and the LLM path with a fake client."""

import json

import pytest

from app.ai.llm_client import LLMError
from app.ai.prompts import TRIP_PARSER_SYSTEM_V1
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
    assert draft.missing_fields == ["origin", "destination", "passengers"]


# --- LLM path ----------------------------------------------------------------------

TEXT = "jutro jadę z Gdyni do Torunia z żoną"
GOOD = {"origin": "Gdynia", "destination": "Toruń", "passengers": 2, "mode": None}


def test_llm_result_is_used_when_valid() -> None:
    client = FakeLLMClient([reply(json.dumps(GOOD))])

    draft = parse_trip(TEXT, client)

    assert draft.parsed_by == "llm"
    assert (draft.origin, draft.destination, draft.passengers) == ("Gdynia", "Toruń", 2)
    request = client.requests[0]
    assert request["response_schema"] == ParsedTrip.model_json_schema()
    assert request["messages"][0] == {"role": "system", "content": TRIP_PARSER_SYSTEM_V1}
    assert TEXT in request["messages"][1]["content"]


def test_llm_missing_fields_are_reported() -> None:
    client = FakeLLMClient([reply('{"origin": null, "destination": "Zakopane", '
                                  '"passengers": null, "mode": null}')])  # fmt: skip

    draft = parse_trip("weekend w Zakopanem", client)

    assert draft.parsed_by == "llm"
    assert draft.missing_fields == ["origin", "passengers"]


@pytest.mark.parametrize(
    "content",
    [
        "Sure! Gdynia to Toruń.",  # not JSON
        '{"origin": "Gdynia", "destination": "Toruń", "passengers": 20, "mode": null}',
        '{"origin": "Gdynia", "destination": "Toruń", "passengers": 2, "mode": "rocket"}',
        '{"origin": "Gdynia", "destination": "Toruń"}',  # missing keys
        '{"origin": "Gdynia", "destination": "Toruń", "passengers": 2, "mode": null, "x": 1}',
        '{"origin": "Gdańsk", "destination": "Toruń", "passengers": 2, "mode": null}',  # invented
    ],
    ids=["not-json", "too-many-passengers", "bad-mode", "missing-keys", "extra-key", "invented"],
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
