"""Shared fixtures: in-memory SQLite per test, and a TestClient wired to it."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.deps import get_llm_client, get_route_provider, get_session, get_weather_service
from app.db import init_db
from app.main import create_app
from tests.fakes import FakeLLMClient, FakeRouteProvider, FakeWeather, make_weather

TripPayload = dict[str, Any]


@pytest.fixture(name="engine")
def engine_fixture() -> Iterator[Engine]:
    # StaticPool keeps a single connection, so the in-memory DB survives across sessions.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture(name="route_provider")
def route_provider_fixture() -> FakeRouteProvider:
    return FakeRouteProvider()


@dataclass
class LLMSlot:
    """Which LLM client the app sees. None = AI disabled (rule-based fallback)."""

    client: FakeLLMClient | None = None


@pytest.fixture(name="llm")
def llm_fixture() -> LLMSlot:
    return LLMSlot()


@pytest.fixture(name="weather")
def weather_fixture() -> FakeWeather:
    """Mild, dry weather by default; tests can change `weather.weather`."""
    return FakeWeather(make_weather())


@pytest.fixture(name="client")
def client_fixture(
    session: Session, route_provider: FakeRouteProvider, llm: LLMSlot, weather: FakeWeather
) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    # Never hit Nominatim/OSRM or Ollama from tests.
    app.dependency_overrides[get_route_provider] = lambda: route_provider
    app.dependency_overrides[get_llm_client] = lambda: llm.client
    app.dependency_overrides[get_weather_service] = lambda: weather
    # Not used as a context manager on purpose: that would run the lifespan,
    # which initialises the on-disk database from settings.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="make_trip_payload")
def make_trip_payload_fixture() -> Callable[..., TripPayload]:
    def _make(**overrides: Any) -> TripPayload:
        payload: TripPayload = {
            "origin": "Warszawa",
            "destination": "Gdańsk",
            "distance_km": 340.0,
            "passengers": 2,
            "mode": "train",
            "note": "Weekend trip",
        }
        payload.update(overrides)
        return payload

    return _make
