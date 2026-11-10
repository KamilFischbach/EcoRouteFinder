"""Persistence for saved comparisons. Queries and writes only."""

from sqlmodel import Session, col, select

from app.models.comparison import Comparison


class ComparisonRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_recent(self, limit: int, offset: int) -> list[Comparison]:
        statement = (
            select(Comparison)
            .order_by(col(Comparison.created_at).desc(), col(Comparison.id).desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def get(self, comparison_id: int) -> Comparison | None:
        return self._session.get(Comparison, comparison_id)

    def save(self, comparison: Comparison) -> Comparison:
        self._session.add(comparison)
        self._session.commit()
        self._session.refresh(comparison)
        return comparison

    def delete(self, comparison: Comparison) -> None:
        self._session.delete(comparison)
        self._session.commit()
