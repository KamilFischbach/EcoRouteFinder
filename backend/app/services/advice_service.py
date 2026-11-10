"""Ask EcoAdvisor about a stored comparison and keep the answer with it."""

from typing import Any

from app.ai.advisor_agent import AdvisorAgent
from app.models.trip import utc_now
from app.services import comparison_snapshot as snapshot
from app.services.comparison_service import ComparisonService


class AdviceService:
    def __init__(self, comparisons: ComparisonService, agent: AdvisorAgent) -> None:
        self._comparisons = comparisons
        self._agent = agent

    def advise(self, comparison_id: int, preferences: str | None = None) -> dict[str, Any]:
        """Return the stored advice JSON.

        Raises NotFoundError for an unknown comparison; otherwise always answers, because the
        agent falls back to rules when the LLM is unavailable or misbehaves.
        """
        saved = self._comparisons.get(comparison_id)
        answer = self._agent.advise(saved.to_result(), preferences)
        advice = snapshot.to_advice_json(answer, utc_now())
        self._comparisons.save_advice(comparison_id, advice, answer.recommended_mode)
        return advice
