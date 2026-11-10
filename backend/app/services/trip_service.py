"""Use cases for saved trips."""

from app.core.errors import NotFoundError
from app.models.trip import TransportMode, Trip, utc_now
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreate, TripUpdate


class TripService:
    def __init__(self, repository: TripRepository) -> None:
        self._repository = repository

    def list_trips(self, mode: TransportMode | None = None) -> list[Trip]:
        return self._repository.list_trips(mode)

    def get_trip(self, trip_id: int) -> Trip:
        trip = self._repository.get(trip_id)
        if trip is None:
            raise NotFoundError("Trip", trip_id)
        return trip

    def create_trip(self, data: TripCreate) -> Trip:
        # TODO(emissions): set co2_kg via services.emissions.calculate_emissions.
        trip = Trip.model_validate(data.model_dump())
        return self._repository.save(trip)

    def update_trip(self, trip_id: int, data: TripUpdate) -> Trip:
        trip = self.get_trip(trip_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(trip, field, value)
        trip.updated_at = utc_now()
        # TODO(emissions): recalculate co2_kg when distance/mode/passengers change.
        return self._repository.save(trip)

    def delete_trip(self, trip_id: int) -> None:
        trip = self.get_trip(trip_id)
        self._repository.delete(trip)
