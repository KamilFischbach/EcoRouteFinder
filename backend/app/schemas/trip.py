"""DTOs for the trips API."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.trip import TransportMode, utc_today

PlaceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
DistanceKm = Annotated[float, Field(gt=0, le=40_000, description="Route length in km")]
Passengers = Annotated[int, Field(ge=1, le=9)]

# UTC+14 is the furthest-ahead time zone: a date is "in the future" only once it hasn't
# started anywhere yet. A user east of UTC can save today's trip just after midnight.
LATEST_UTC_OFFSET = timedelta(hours=14)


def latest_travel_date() -> date:
    return (datetime.now(UTC) + LATEST_UTC_OFFSET).date()


def _not_in_future(value: date) -> date:
    if value > latest_travel_date():
        raise ValueError("Travel date cannot be in the future")
    return value


TravelDate = Annotated[date, AfterValidator(_not_in_future)]

NULLABLE_UPDATE_FIELDS = frozenset({"note"})


class TripCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: PlaceName
    destination: PlaceName
    distance_km: DistanceKm
    passengers: Passengers = 1
    mode: TransportMode
    note: Note | None = None
    travelled_on: TravelDate = Field(default_factory=utc_today)

    @field_validator("note")
    @classmethod
    def _blank_note_to_none(cls, value: str | None) -> str | None:
        return value or None


class TripUpdate(BaseModel):
    """Partial update: only fields present in the request body are changed."""

    model_config = ConfigDict(extra="forbid")

    origin: PlaceName | None = None
    destination: PlaceName | None = None
    distance_km: DistanceKm | None = None
    passengers: Passengers | None = None
    mode: TransportMode | None = None
    note: Note | None = None
    travelled_on: TravelDate | None = None

    @field_validator("note")
    @classmethod
    def _blank_note_to_none(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def _reject_null_for_required(self) -> Self:
        nulled = sorted(
            name
            for name in self.model_fields_set - NULLABLE_UPDATE_FIELDS
            if getattr(self, name) is None
        )
        if nulled:
            raise ValueError(f"Fields cannot be null: {', '.join(nulled)}")
        return self


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origin: str
    destination: str
    distance_km: float
    passengers: int
    mode: TransportMode
    co2_kg: float | None
    note: str | None
    travelled_on: date
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        # SQLite drops tzinfo; values are always stored in UTC.
        return value if value.tzinfo else value.replace(tzinfo=UTC)
