"""Unit tests for TripService (real repository on an in-memory DB, no HTTP)."""

import pytest
from sqlmodel import Session

from app.core.errors import NotFoundError
from app.models.trip import TransportMode
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreate, TripUpdate
from app.services.trip_service import TripService


@pytest.fixture(name="service")
def service_fixture(session: Session) -> TripService:
    return TripService(TripRepository(session))


def _new_trip(**overrides: object) -> TripCreate:
    data: dict[str, object] = {
        "origin": "Poznań",
        "destination": "Berlin",
        "distance_km": 270,
        "passengers": 1,
        "mode": TransportMode.TRAIN,
    }
    data.update(overrides)
    return TripCreate.model_validate(data)


def test_create_trip_persists_and_leaves_co2_empty(service: TripService) -> None:
    trip = service.create_trip(_new_trip())

    assert trip.id is not None
    assert trip.co2_kg is None
    assert service.get_trip(trip.id) == trip


def test_update_trip_applies_partial_changes_and_bumps_updated_at(service: TripService) -> None:
    trip = service.create_trip(_new_trip())
    assert trip.id is not None
    previous_updated_at = trip.updated_at

    updated = service.update_trip(trip.id, TripUpdate(passengers=3))

    assert updated.passengers == 3
    assert updated.origin == "Poznań"
    assert updated.updated_at >= previous_updated_at


def test_list_trips_filters_by_mode(service: TripService) -> None:
    service.create_trip(_new_trip(mode=TransportMode.TRAIN))
    service.create_trip(_new_trip(mode=TransportMode.BIKE))

    bikes = service.list_trips(TransportMode.BIKE)

    assert [trip.mode for trip in bikes] == [TransportMode.BIKE]


@pytest.mark.parametrize("action", ["get", "update", "delete"])
def test_missing_trip_raises_not_found(service: TripService, action: str) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        if action == "get":
            service.get_trip(42)
        elif action == "update":
            service.update_trip(42, TripUpdate(passengers=2))
        else:
            service.delete_trip(42)

    assert exc_info.value.details == {"resource": "Trip", "id": 42}
