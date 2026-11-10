"""Database engine, session dependency and schema initialisation."""

import json
from collections.abc import Iterator

from sqlalchemy import Connection, inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings
from app.services import comparison_snapshot


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


engine = build_engine(get_settings().database_url)


def init_db(bind: Engine = engine) -> None:
    """Create missing tables and upgrade old data. Called once on application startup."""
    import app.models  # noqa: F401  (registers table models on SQLModel.metadata)

    SQLModel.metadata.create_all(bind)
    with bind.begin() as conn:
        _upgrade_comparisons_to_v2(conn)


# TODO(db): replace these hand-written steps with Alembic before the next schema change.
def _upgrade_comparisons_to_v2(conn: Connection) -> None:
    """Snapshot version 2 renamed `solo_car_co2_kg` (one person driving alone) to
    `petrol_car_co2_kg` (the same group by petrol car). Converts old rows in place, keeping
    the history. Safe to run on every start: it does nothing once the data is upgraded."""
    columns = {column["name"] for column in inspect(conn).get_columns("comparison")}
    if "solo_car_co2_kg" in columns and "petrol_car_co2_kg" not in columns:
        conn.execute(
            text("ALTER TABLE comparison RENAME COLUMN solo_car_co2_kg TO petrol_car_co2_kg")
        )
    rows = conn.execute(
        text("SELECT id, result FROM comparison WHERE json_extract(result, '$.version') = 1")
    ).all()
    for row_id, raw in rows:
        upgraded = comparison_snapshot.upgrade_snapshot(json.loads(raw))
        conn.execute(
            text(
                "UPDATE comparison SET result = :result, petrol_car_co2_kg = :baseline"
                " WHERE id = :id"
            ),
            {
                "result": json.dumps(upgraded),
                "baseline": comparison_snapshot.petrol_car_co2_kg(upgraded),
                "id": row_id,
            },
        )


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding one session per request."""
    with Session(engine) as session:
        yield session
