"""DTOs for trip drafts: free text in, a form pre-fill out. Nothing is stored."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.trip import TransportMode

DraftText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class TripDraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: DraftText


class TripDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    origin: str | None
    destination: str | None
    passengers: int | None
    mode: TransportMode | None
    missing_fields: list[Literal["origin", "destination", "passengers"]]
    parsed_by: Literal["llm", "rules"]
