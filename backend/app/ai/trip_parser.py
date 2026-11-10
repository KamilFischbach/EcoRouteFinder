"""Free-text -> structured trip parser ("Warsaw to Gdansk, 3 people, by train").

Flow (TODO):
1. If an `LLMClient` is available: call it with `prompts.TRIP_PARSER_SYSTEM_V1` and
   `ParsedTrip.model_json_schema()` as structured-output schema; validate the reply with Pydantic.
2. On any failure (client down, invalid JSON, validation error): use `parse_trip_with_rules`.
The parser never returns distances or emissions; those come from services.
"""

from pydantic import BaseModel, Field

from app.ai.llm_client import LLMClient
from app.models.trip import TransportMode


class ParsedTrip(BaseModel):
    origin: str | None = None
    destination: str | None = None
    passengers: int | None = Field(default=None, ge=1, le=9)
    mode: TransportMode | None = None


def parse_trip(text: str, client: LLMClient | None) -> ParsedTrip:
    """Parse with the LLM when possible, otherwise fall back to rules. Not implemented yet."""
    raise NotImplementedError("TODO: LLM parser with rule-based fallback")


def parse_trip_with_rules(text: str) -> ParsedTrip:
    """Regex/keyword fallback (e.g. 'from X to Y', 'N people', mode keywords). Not implemented."""
    raise NotImplementedError("TODO: rule-based parser")
