"""Persistence for `Trip`. No business rules here, only queries and writes."""

from datetime import date

from sqlmodel import Session, col, select

from app.models.trip import TransportMode, Trip


class TripRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_trips(self, mode: TransportMode | None = None) -> list[Trip]:
        statement = select(Trip).order_by(
            col(Trip.travelled_on).desc(), col(Trip.created_at).desc(), col(Trip.id).desc()
        )
        if mode is not None:
            statement = statement.where(col(Trip.mode) == mode)
        return list(self._session.exec(statement).all())

    def list_travelled_since(self, start: date | None) -> list[Trip]:
        """Trips travelled on or after `start` (all trips when None), in one query."""
        statement = select(Trip).order_by(col(Trip.travelled_on), col(Trip.id))
        if start is not None:
            statement = statement.where(col(Trip.travelled_on) >= start)
        return list(self._session.exec(statement).all())

    def get(self, trip_id: int) -> Trip | None:
        return self._session.get(Trip, trip_id)

    def save(self, trip: Trip) -> Trip:
        self._session.add(trip)
        self._session.commit()
        self._session.refresh(trip)
        return trip

    def delete(self, trip: Trip) -> None:
        self._session.delete(trip)
        self._session.commit()
