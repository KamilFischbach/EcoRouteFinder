"""Upgrading an old database (snapshot version 1, trips without a travel date) keeps the data."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.db import build_engine, init_db
from app.models.trip import TransportMode
from app.repositories.comparison_repository import ComparisonRepository
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreate
from app.services import comparison_snapshot as snapshot
from app.services.comparison_service import ComparisonService
from app.services.trip_service import TripService
from tests.fakes import FakeRouteProvider

# Version 1 snapshot for 2 people: savings were measured against ONE person driving alone
# (47.39 kg). The petrol car shared by 2 is 23.69 kg each.
V1_SNAPSHOT: dict[str, Any] = {
    "version": 1,
    "options": [
        {"mode": "train", "distance_km": 302.4, "duration_min": 217, "cost_pln": 90.72,
         "co2_kg": 9.35, "co2_saved_vs_car_kg": 38.04, "practical": True, "note": None},
        {"mode": "car_petrol", "distance_km": 293.4, "duration_min": 180, "cost_pln": 66.02,
         "co2_kg": 23.69, "co2_saved_vs_car_kg": 23.7, "practical": True, "note": None},
        {"mode": "plane", "distance_km": 252.0, "duration_min": 151, "cost_pln": 201.6,
         "co2_kg": 57.78, "co2_saved_vs_car_kg": -10.39, "practical": False,
         "note": "Not worth flying under 300 km."},
    ],
    "highlights": {"greenest": "train", "fastest": "car_petrol", "cheapest": "car_petrol"},
}  # fmt: skip

LEGACY_COMPARISON_TABLE = """
CREATE TABLE comparison (
    id INTEGER PRIMARY KEY, origin VARCHAR(120) NOT NULL, destination VARCHAR(120) NOT NULL,
    passengers INTEGER NOT NULL, distance_km FLOAT, origin_name VARCHAR NOT NULL,
    origin_lat FLOAT, origin_lon FLOAT, destination_name VARCHAR NOT NULL,
    destination_lat FLOAT, destination_lon FLOAT, road_km FLOAT NOT NULL, source VARCHAR NOT NULL,
    result JSON NOT NULL, advice JSON, greenest_mode VARCHAR(10), greenest_co2_kg FLOAT,
    solo_car_co2_kg FLOAT NOT NULL, recommended_mode VARCHAR(10), created_at DATETIME NOT NULL
)
"""


LEGACY_TRIP_TABLE = """
CREATE TABLE trip (
    id INTEGER PRIMARY KEY, origin VARCHAR(120) NOT NULL, destination VARCHAR(120) NOT NULL,
    distance_km FLOAT NOT NULL, passengers INTEGER NOT NULL, mode VARCHAR(10) NOT NULL,
    co2_kg FLOAT, note VARCHAR(500), created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
)
"""


@pytest.fixture(name="legacy_engine")
def legacy_engine_fixture(tmp_path: Path) -> Engine:
    """A file database shaped like one created before snapshot version 2."""
    engine = build_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(text(LEGACY_COMPARISON_TABLE))
        conn.execute(
            text(
                "INSERT INTO comparison (id, origin, destination, passengers, origin_name,"
                " destination_name, road_km, source, result, advice, greenest_mode,"
                " greenest_co2_kg, solo_car_co2_kg, recommended_mode, created_at)"
                " VALUES (1, 'Warszawa', 'Kraków', 2, 'Warszawa', 'Kraków', 293.4, 'osrm',"
                " :result, :advice, 'TRAIN', 9.35, 47.39, 'TRAIN', '2026-11-09 10:00:00')"
            ),
            {"result": json.dumps(V1_SNAPSHOT), "advice": json.dumps({"summary": "Old advice"})},
        )
        conn.execute(text(LEGACY_TRIP_TABLE))
        conn.execute(
            text(
                "INSERT INTO trip (id, origin, destination, distance_km, passengers, mode,"
                " co2_kg, note, created_at, updated_at) VALUES (1, 'Warszawa', 'Kraków', 293.4,"
                " 1, 'TRAIN', 9.07, NULL, '2026-10-03 22:30:00', '2026-10-03 22:30:00')"
            )
        )
    return engine


def test_upgrade_snapshot_recomputes_savings_against_the_group_by_petrol_car() -> None:
    upgraded = snapshot.upgrade_snapshot(V1_SNAPSHOT)

    assert upgraded["version"] == snapshot.SNAPSHOT_VERSION
    saved = {o["mode"]: o["co2_saved_vs_petrol_car_kg"] for o in upgraded["options"]}
    assert saved == {"train": 14.34, "car_petrol": 0.0, "plane": -34.09}
    assert all("co2_saved_vs_car_kg" not in o for o in upgraded["options"])
    assert upgraded["highlights"] == V1_SNAPSHOT["highlights"]
    assert snapshot.petrol_car_co2_kg(upgraded) == 23.69


def test_upgrade_snapshot_leaves_current_snapshots_alone() -> None:
    current = snapshot.to_snapshot(
        ComparisonService(FakeRouteProvider()).compute("Warszawa", "Kraków", 2)
    )

    assert snapshot.upgrade_snapshot(current) == current


def test_init_db_upgrades_a_legacy_database(legacy_engine: Engine) -> None:
    init_db(legacy_engine)

    columns = {c["name"] for c in inspect(legacy_engine).get_columns("comparison")}
    assert "petrol_car_co2_kg" in columns
    assert "solo_car_co2_kg" not in columns
    with Session(legacy_engine) as session:
        repository = ComparisonRepository(session)
        record = repository.get(1)
        assert record is not None
        saved = snapshot.to_saved(record)
        assert record.petrol_car_co2_kg == 23.69
        assert [o.co2_saved_vs_petrol_car_kg for o in saved.options] == [14.34, 0.0, -34.09]
        assert saved.advice == {"summary": "Old advice"}  # history and advice are kept
        summary = snapshot.to_summary(record)
        assert summary.petrol_car_co2_kg == 23.69


def test_upgraded_database_accepts_new_comparisons(legacy_engine: Engine) -> None:
    init_db(legacy_engine)

    with Session(legacy_engine) as session:
        service = ComparisonService(FakeRouteProvider(), ComparisonRepository(session))
        created = service.create("Warszawa", "Kraków", passengers=2)
        assert [c.id for c in service.list_recent()] == [created.id, 1]


def test_init_db_upgrade_runs_only_once(legacy_engine: Engine) -> None:
    init_db(legacy_engine)
    init_db(legacy_engine)

    with Session(legacy_engine) as session:
        record = ComparisonRepository(session).get(1)
        assert record is not None
        assert record.petrol_car_co2_kg == 23.69
        assert record.result["version"] == snapshot.SNAPSHOT_VERSION


def test_init_db_gives_old_trips_their_save_date_as_travel_date(legacy_engine: Engine) -> None:
    init_db(legacy_engine)
    init_db(legacy_engine)  # idempotent

    with Session(legacy_engine) as session:
        repository = TripRepository(session)
        trip = repository.get(1)
        assert trip is not None
        assert trip.travelled_on == date(2026, 10, 3)
        assert trip.co2_kg == 9.07
        service = TripService(repository)
        new = service.create_trip(
            TripCreate(origin="A", destination="B", distance_km=10, mode=TransportMode.BIKE)
        )
        assert [t.id for t in service.list_trips()] == [new.id, 1]
    indexes = {i["name"] for i in inspect(legacy_engine).get_indexes("trip")}
    assert "ix_trip_travelled_on" in indexes
