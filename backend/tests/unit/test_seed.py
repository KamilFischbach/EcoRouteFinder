from datetime import date

import pytest
from sqlmodel import Session

from app.models.trip import TransportMode
from app.repositories.trip_repository import TripRepository
from app.seed import HISTORY_DAYS, MODE_PLAN, seed
from app.services.emissions import calculate_emissions
from app.services.stats import StatsRange, StatsService
from app.services.trip_service import TripService

TODAY = date(2026, 11, 10)


@pytest.fixture(name="service")
def service_fixture(session: Session) -> TripService:
    return TripService(TripRepository(session))


def test_seed_adds_demo_trips_with_computed_co2(service: TripService) -> None:
    added = seed(service, today=TODAY)

    trips = service.list_trips()
    assert added == len(trips) == len(MODE_PLAN) == 30
    for trip in trips:
        expected = calculate_emissions(trip.distance_km, trip.mode, trip.passengers)
        assert trip.co2_kg == round(expected, 2)
        assert 0 <= (TODAY - trip.travelled_on).days < HISTORY_DAYS
    modes = [trip.mode for trip in trips]
    assert modes.count(TransportMode.TRAIN) > modes.count(TransportMode.CAR_PETROL) > 0
    assert modes.count(TransportMode.PLANE) == 2


def test_seed_is_deterministic(session: Session, service: TripService) -> None:
    seed(service, today=TODAY)
    first = [(t.origin, t.mode, t.passengers, t.travelled_on) for t in service.list_trips()]
    for trip in service.list_trips():
        service.delete_trip(trip.id or 0)

    seed(service, today=TODAY)

    assert [(t.origin, t.mode, t.passengers, t.travelled_on) for t in service.list_trips()] == first


def test_seed_refuses_a_database_with_trips(service: TripService) -> None:
    seed(service, today=TODAY)

    assert seed(service, today=TODAY) == 0
    assert len(service.list_trips()) == 30


def test_seed_with_force_only_adds(service: TripService) -> None:
    seed(service, today=TODAY)

    assert seed(service, force=True, today=TODAY) == 30
    assert len(service.list_trips()) == 60


def test_demo_data_reaches_the_middle_level_in_90_days(session: Session) -> None:
    repository = TripRepository(session)
    seed(TripService(repository), today=TODAY)

    stats = StatsService(repository).get_stats(StatsRange.DAYS_90, today=TODAY)

    assert stats.level.name == "Sapling"
    assert stats.totals.trips > 15
