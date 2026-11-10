"""FastAPI dependencies. Wires repositories into services so routers only see services."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.ai.llm_client import LLMClient, build_llm_client
from app.core.config import get_settings
from app.db import get_session
from app.repositories.comparison_repository import ComparisonRepository
from app.repositories.trip_repository import TripRepository
from app.services.comparison_service import ComparisonService
from app.services.routing import RouteProvider, build_route_provider
from app.services.trip_service import TripService

SessionDep = Annotated[Session, Depends(get_session)]


def get_trip_service(session: SessionDep) -> TripService:
    return TripService(TripRepository(session))


TripServiceDep = Annotated[TripService, Depends(get_trip_service)]


@lru_cache
def get_route_provider() -> RouteProvider:
    """One provider per process, so the HTTP client and geocoding cache are shared."""
    return build_route_provider(get_settings())


def get_comparison_service(
    session: SessionDep,
    route_provider: Annotated[RouteProvider, Depends(get_route_provider)],
) -> ComparisonService:
    return ComparisonService(route_provider, ComparisonRepository(session))


ComparisonServiceDep = Annotated[ComparisonService, Depends(get_comparison_service)]


@lru_cache
def get_llm_client() -> LLMClient | None:
    """One client per process, so the availability cache is shared. None when AI is disabled."""
    return build_llm_client(get_settings())


LLMClientDep = Annotated[LLMClient | None, Depends(get_llm_client)]
