"""Database engine, session dependency and schema initialisation."""

from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


engine = build_engine(get_settings().database_url)


def init_db(bind: Engine = engine) -> None:
    """Create all tables. Called once on application startup."""
    import app.models  # noqa: F401  (registers table models on SQLModel.metadata)

    SQLModel.metadata.create_all(bind)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding one session per request."""
    with Session(engine) as session:
        yield session
