"""FastAPI dependencies. Wires repositories into services so routers only see services."""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.db import get_session
from app.repositories.trip_repository import TripRepository
from app.services.trip_service import TripService

SessionDep = Annotated[Session, Depends(get_session)]


def get_trip_service(session: SessionDep) -> TripService:
    return TripService(TripRepository(session))


TripServiceDep = Annotated[TripService, Depends(get_trip_service)]
