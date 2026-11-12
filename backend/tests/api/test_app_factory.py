"""The application factory builds its own database engine from the settings it is given."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import Settings
from app.db import build_engine
from app.main import create_app
from app.models.trip import Trip


def test_create_app_uses_the_database_from_its_settings(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'factory.db'}"
    app = create_app(Settings(database_url=database_url, ai_enabled=False))
    payload = {"origin": "Gdynia", "destination": "Sopot", "distance_km": 12, "mode": "bike"}

    # The context manager runs the lifespan, which creates the tables in that database.
    with TestClient(app) as client:
        response = client.post("/api/v1/trips", json=payload)

    assert response.status_code == 201
    engine = build_engine(database_url)
    with Session(engine) as session:
        assert [trip.origin for trip in session.exec(select(Trip))] == ["Gdynia"]
    engine.dispose()


def test_each_app_gets_its_own_engine(tmp_path: Path) -> None:
    first = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'a.db'}"))
    second = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'b.db'}"))

    assert first.state.engine is not second.state.engine
    assert str(first.state.engine.url).endswith("a.db")
