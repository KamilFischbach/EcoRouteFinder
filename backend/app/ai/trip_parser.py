"""Free text -> trip draft ("jutro jadę z Gdyni do Torunia z żoną").

1. If an LLM is available: ask it with `TRIP_PARSER_SYSTEM_V1` and `ParsedTrip`'s JSON schema as
   structured output, validate the reply with Pydantic, and check the places really occur in the
   text (a cheap guard against invented names).
2. On any failure (no client, offline, timeout, bad JSON, schema violation, invented place):
   fall back to `parse_trip_with_rules`.
The parser never returns distances or emissions; those come from services.
"""

import logging
import unicodedata
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.ai import trip_rules
from app.ai.llm_client import LLMClient, LLMError, system_message, user_message
from app.ai.prompts import TRIP_PARSER_SYSTEM_V1
from app.models.trip import TransportMode

logger = logging.getLogger(__name__)

ParsedBy = Literal["llm", "rules"]
# Fields the compare form needs. `mode` is optional, so it is never "missing".
REQUIRED_FIELDS = ("origin", "destination", "passengers")
# Polish declension changes word endings ("Gdynia" -> "z Gdyni"); compare only the stem.
STEM_LENGTH = 3

PlaceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ParsedTrip(BaseModel):
    """What the LLM must return. Its JSON schema is sent to Ollama as `format`."""

    model_config = ConfigDict(extra="forbid")

    origin: PlaceName | None
    destination: PlaceName | None
    passengers: Annotated[int, Field(ge=1, le=9)] | None
    mode: TransportMode | None


@dataclass(frozen=True)
class TripDraft:
    origin: str | None
    destination: str | None
    passengers: int | None
    mode: TransportMode | None
    missing_fields: list[str]
    parsed_by: ParsedBy


def _fold(text: str) -> str:
    """Lowercase, without diacritics ("Łódź" -> "lodz")."""
    decomposed = unicodedata.normalize("NFKD", text.lower().replace("ł", "l"))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _occurs_in(place: str, text: str) -> bool:
    folded_text = _fold(text)
    return all(_fold(word)[:STEM_LENGTH] in folded_text for word in place.split())


def _to_draft(parsed: ParsedTrip, parsed_by: ParsedBy) -> TripDraft:
    missing = [name for name in REQUIRED_FIELDS if getattr(parsed, name) is None]
    return TripDraft(
        origin=parsed.origin,
        destination=parsed.destination,
        passengers=parsed.passengers,
        mode=parsed.mode,
        missing_fields=missing,
        parsed_by=parsed_by,
    )


def parse_trip_with_rules(text: str) -> TripDraft:
    origin, destination = trip_rules.find_route(text)
    parsed = ParsedTrip(
        origin=origin,
        destination=destination,
        passengers=trip_rules.find_passengers(text),
        mode=trip_rules.find_mode(text),
    )
    return _to_draft(parsed, "rules")


def _parse_with_llm(text: str, client: LLMClient) -> ParsedTrip:
    response = client.chat(
        [system_message(TRIP_PARSER_SYSTEM_V1), user_message(f"Message: {text}")],
        response_schema=ParsedTrip.model_json_schema(),
    )
    parsed = ParsedTrip.model_validate_json(response.content)
    for place in (parsed.origin, parsed.destination):
        if place is not None and not _occurs_in(place, text):
            raise ValueError(f"LLM returned a place that is not in the text: {place!r}")
    return parsed


def parse_trip(text: str, client: LLMClient | None) -> TripDraft:
    """Parse with the LLM when possible, otherwise with rules. Never raises for bad LLM output."""
    if client is not None and client.is_available():
        try:
            return _to_draft(_parse_with_llm(text, client), "llm")
        except (LLMError, ValidationError, ValueError) as exc:
            logger.info("LLM trip parsing failed, using rules: %s", exc)
    return parse_trip_with_rules(text)
