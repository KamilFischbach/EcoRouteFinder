"""`Comparison` table: a saved comparison with a frozen snapshot of what the user saw.

`result` stores options + highlights as JSON. Factors may change later; history must keep
showing the numbers from the moment of the comparison, so nothing is recomputed on read.
The `greenest_*`, `solo_car_co2_kg` and `recommended_mode` columns duplicate a few snapshot
values so the history list doesn't have to parse JSON for every row.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.trip import TransportMode, utc_now


class Comparison(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    # Input as typed by the user.
    origin: str = Field(max_length=120)
    destination: str = Field(max_length=120)
    passengers: int
    distance_km: float | None = None

    # Resolved route.
    origin_name: str
    origin_lat: float | None = None
    origin_lon: float | None = None
    destination_name: str
    destination_lat: float | None = None
    destination_lon: float | None = None
    road_km: float
    source: str  # "osrm" | "estimate" | "user"

    # Snapshot and advice (JSON).
    result: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    advice: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    # Denormalised for the history list.
    greenest_mode: TransportMode | None = None
    greenest_co2_kg: float | None = None
    solo_car_co2_kg: float
    recommended_mode: TransportMode | None = None

    created_at: datetime = Field(default_factory=utc_now, index=True)
