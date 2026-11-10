"""Demo data for the dashboard: about 30 trips from the last ~4 months.

Usage (from backend/, never run automatically):

    python -m app.seed            # only into a database without trips
    python -m app.seed --force    # add the demo trips next to existing ones (nothing is deleted)

Trips go through `TripService`, so CO2 is computed by `services/emissions.py`. A fixed random
seed makes the data the same on every run.
"""

import argparse
import random
from dataclasses import dataclass
from datetime import date, timedelta

from sqlmodel import Session

from app.db import engine, init_db
from app.models.trip import TransportMode, utc_today
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreate
from app.services.trip_service import TripService

RANDOM_SEED = 2026
HISTORY_DAYS = 120
M = TransportMode


@dataclass(frozen=True)
class DemoRoute:
    origin: str
    destination: str
    distance_km: float


# Rough road distances between Polish cities.
SHORT_ROUTES = (
    DemoRoute("Kraków", "Wieliczka", 15),
    DemoRoute("Gdańsk", "Sopot", 13),
    DemoRoute("Warszawa", "Konstancin-Jeziorna", 22),
    DemoRoute("Wrocław", "Oława", 30),
    DemoRoute("Poznań", "Kórnik", 24),
)
REGIONAL_ROUTES = (
    DemoRoute("Warszawa", "Łódź", 135),
    DemoRoute("Kraków", "Katowice", 80),
    DemoRoute("Kraków", "Zakopane", 110),
    DemoRoute("Gdańsk", "Toruń", 180),
    DemoRoute("Wrocław", "Opole", 100),
    DemoRoute("Poznań", "Bydgoszcz", 130),
)
FLIGHT_ROUTES = (DemoRoute("Kraków", "Gdańsk", 590), DemoRoute("Wrocław", "Gdańsk", 480))
LONG_ROUTES = (
    DemoRoute("Warszawa", "Kraków", 295),
    DemoRoute("Warszawa", "Gdańsk", 340),
    DemoRoute("Warszawa", "Poznań", 310),
    DemoRoute("Wrocław", "Warszawa", 345),
    DemoRoute("Kraków", "Gdańsk", 590),
)

# 30 trips: mostly trains, some cars, a few bikes and two flights.
MODE_PLAN: tuple[TransportMode, ...] = (
    (M.TRAIN,) * 13 + (M.COACH,) * 4 + (M.CAR_PETROL,) * 5 + (M.CAR_EV,) * 2 + (M.BIKE,) * 4
) + (M.PLANE,) * 2


def demo_trips(today: date, rng: random.Random) -> list[TripCreate]:
    """The demo trips, oldest first, spread evenly over `HISTORY_DAYS` with some jitter.
    Deterministic for a given `rng` seed and `today`."""
    modes = list(MODE_PLAN)
    rng.shuffle(modes)
    step = HISTORY_DAYS // len(modes)
    trips = [
        _demo_trip(mode, today - timedelta(days=i * step + rng.randrange(step)), rng)
        for i, mode in enumerate(modes)
    ]
    return sorted(trips, key=lambda trip: trip.travelled_on)


def _demo_trip(mode: TransportMode, travelled_on: date, rng: random.Random) -> TripCreate:
    route = rng.choice(_routes_for(mode))
    return TripCreate(
        origin=route.origin,
        destination=route.destination,
        distance_km=route.distance_km,
        passengers=_passengers(mode, rng),
        mode=mode,
        travelled_on=travelled_on,
    )


def _routes_for(mode: TransportMode) -> tuple[DemoRoute, ...]:
    if mode is M.BIKE:
        return SHORT_ROUTES
    if mode is M.PLANE:
        return FLIGHT_ROUTES
    return REGIONAL_ROUTES + LONG_ROUTES


def _passengers(mode: TransportMode, rng: random.Random) -> int:
    if mode in (M.CAR_PETROL, M.CAR_EV):
        return rng.randint(1, 4)
    if mode is M.BIKE:
        return 1
    return rng.choice((1, 1, 1, 2, 3))


def seed(service: TripService, *, force: bool = False, today: date | None = None) -> int:
    """Add the demo trips and return how many were added. Refuses (returns 0) when the
    database already has trips, unless `force`. Never deletes anything."""
    if service.list_trips() and not force:
        return 0
    trips = demo_trips(today or utc_today(), random.Random(RANDOM_SEED))
    for trip in trips:
        service.create_trip(trip)
    return len(trips)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed", description="Add demo trips for the dashboard."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="add the demo trips even if the database already has trips (nothing is deleted)",
    )
    args = parser.parse_args(argv)
    init_db()
    with Session(engine) as session:
        added = seed(TripService(TripRepository(session)), force=args.force)
    if added == 0:
        print("The database already has trips; nothing added. Use --force to add demo trips.")
        return 1
    print(f"Added {added} demo trips.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
