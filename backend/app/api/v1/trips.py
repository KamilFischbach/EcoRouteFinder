"""Trips endpoints. Thin: parse input, call the service, shape the output."""

from fastapi import APIRouter, status

from app.api.deps import TripServiceDep
from app.models.trip import TransportMode
from app.schemas.trip import TripCreate, TripRead, TripUpdate

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("")
def list_trips(service: TripServiceDep, mode: TransportMode | None = None) -> list[TripRead]:
    return [TripRead.model_validate(trip) for trip in service.list_trips(mode)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, service: TripServiceDep) -> TripRead:
    return TripRead.model_validate(service.create_trip(payload))


@router.get("/{trip_id}")
def get_trip(trip_id: int, service: TripServiceDep) -> TripRead:
    return TripRead.model_validate(service.get_trip(trip_id))


@router.put("/{trip_id}")
def update_trip(trip_id: int, payload: TripUpdate, service: TripServiceDep) -> TripRead:
    return TripRead.model_validate(service.update_trip(trip_id, payload))


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: int, service: TripServiceDep) -> None:
    service.delete_trip(trip_id)
