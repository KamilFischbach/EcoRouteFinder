"""Snapshot mapping: a stored comparison reads back exactly as it was computed."""

import json
from datetime import date

from sqlmodel import Session

from app.models.comparison import Comparison
from app.repositories.comparison_repository import ComparisonRepository
from app.services import comparison_snapshot as snapshot
from app.services.comparison_models import ComparisonResult
from app.services.comparison_service import ComparisonService
from tests.fakes import FakeRouteProvider


def _result() -> ComparisonResult:
    return ComparisonService(FakeRouteProvider()).compute("Warszawa", "Kraków", passengers=2)


def test_snapshot_is_plain_json() -> None:
    data = snapshot.to_snapshot(_result())

    assert json.loads(json.dumps(data)) == data
    assert data["version"] == 2
    assert data["highlights"] == {"greenest": "train", "fastest": "car_ev", "cheapest": "car_ev"}


def test_round_trip_through_the_database(session: Session) -> None:
    result = _result()
    record = snapshot.to_record(result, "warszawa", "krakow", None, date(2026, 11, 14))

    saved = ComparisonRepository(session).save(record)
    session.expire_all()
    reloaded = session.get(Comparison, saved.id)
    assert reloaded is not None
    restored = snapshot.to_saved(reloaded)

    assert restored.to_result() == result
    assert restored.advice is None
    assert reloaded.origin == "warszawa"  # input kept as typed
    assert reloaded.origin_name == "Warszawa"  # resolved name
    assert restored.travelled_on == date(2026, 11, 14)


def test_record_denormalises_summary_fields() -> None:
    result = _result()

    record = snapshot.to_record(result, "A", "B", None, date(2026, 11, 10))

    assert record.greenest_mode == "train"
    assert record.greenest_co2_kg == 9.35
    assert record.petrol_car_co2_kg == 23.69  # same group of 2 by petrol car, per person
    assert record.recommended_mode is None
