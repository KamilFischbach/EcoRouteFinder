"""FastAPI dependencies. Wires repositories into services so routers only see services."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.ai.advisor_agent import AdvisorAgent
from app.ai.llm_client import LLMClient, build_llm_client
from app.ai.tools import build_tool_registry
from app.core.config import get_settings
from app.repositories.comparison_repository import ComparisonRepository
from app.repositories.trip_repository import TripRepository
from app.services.advice_service import AdviceService
from app.services.comparison_service import ComparisonService
from app.services.routing import RouteProvider, build_route_provider
from app.services.stats import StatsService
from app.services.trip_service import TripService
from app.services.weather import WeatherProvider, build_weather_service


def get_session(request: Request) -> Iterator[Session]:
    """One session per request, on the engine `create_app` keeps in `app.state`."""
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_trip_service(session: SessionDep) -> TripService:
    return TripService(TripRepository(session))


TripServiceDep = Annotated[TripService, Depends(get_trip_service)]


def get_stats_service(session: SessionDep) -> StatsService:
    return StatsService(TripRepository(session))


StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]


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


@lru_cache
def get_weather_service() -> WeatherProvider:
    """One Open-Meteo client per process (shared cache); geocodes with the route provider."""
    return build_weather_service(get_settings(), get_route_provider())


def get_advice_service(
    comparisons: ComparisonServiceDep,
    llm_client: LLMClientDep,
    weather: Annotated[WeatherProvider, Depends(get_weather_service)],
) -> AdviceService:
    tools = build_tool_registry(comparisons, weather)
    return AdviceService(comparisons, AdvisorAgent(llm_client, tools, weather))


AdviceServiceDep = Annotated[AdviceService, Depends(get_advice_service)]
