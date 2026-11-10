"""Use cases for saved trips."""

from app.core.errors import NotFoundError
from app.models.trip import TransportMode, Trip, utc_now
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreate, TripUpdate
from app.services.emissions import calculate_emissions


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
        trip = Trip.model_validate(data.model_dump())
        trip.co2_kg = self._co2_per_person(trip)
        return self._repository.save(trip)

    def update_trip(self, trip_id: int, data: TripUpdate) -> Trip:
        trip = self.get_trip(trip_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(trip, field, value)
        trip.co2_kg = self._co2_per_person(trip)
        trip.updated_at = utc_now()
        return self._repository.save(trip)

    @staticmethod
    def _co2_per_person(trip: Trip) -> float:
        return round(calculate_emissions(trip.distance_km, trip.mode, trip.passengers), 2)

    def delete_trip(self, trip_id: int) -> None:
        trip = self.get_trip(trip_id)
        self._repository.delete(trip)
