"""`Trip` table: a saved route in the user's history."""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class TransportMode(StrEnum):
    CAR_PETROL = "car_petrol"
    CAR_EV = "car_ev"
    TRAIN = "train"
    COACH = "coach"
    PLANE = "plane"
    BIKE = "bike"


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_today() -> date:
    return utc_now().date()


class Trip(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    origin: str = Field(max_length=120)
    destination: str = Field(max_length=120)
    distance_km: float
    passengers: int
    mode: TransportMode = Field(index=True)
    # Per person. TripService sets it from services/emissions.py on every create and update;
    # never by an LLM. Nullable only so rows saved before emissions existed stay valid.
    co2_kg: float | None = None
    note: str | None = Field(default=None, max_length=500)
    # The day of the journey (chosen by the user); statistics group trips by it.
    travelled_on: date = Field(default_factory=utc_today, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
