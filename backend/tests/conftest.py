"""Shared fixtures: in-memory SQLite per test, and a TestClient wired to it."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.deps import get_route_provider
from app.db import get_session, init_db
from app.main import create_app
from tests.fakes import FakeRouteProvider

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


@pytest.fixture(name="client")
def client_fixture(session: Session, route_provider: FakeRouteProvider) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    # Never hit Nominatim/OSRM from tests.
    app.dependency_overrides[get_route_provider] = lambda: route_provider
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
