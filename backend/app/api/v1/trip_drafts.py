"""Trip drafts: turn a free-text description into a pre-filled compare form."""

from fastapi import APIRouter

from app.ai.trip_parser import parse_trip
from app.api.deps import LLMClientDep
from app.schemas.trip_draft import TripDraftCreate, TripDraftRead

router = APIRouter(prefix="/trip-drafts", tags=["ai"])


@router.post("")
def create_trip_draft(payload: TripDraftCreate, llm_client: LLMClientDep) -> TripDraftRead:
    """Always 200: when the LLM is unavailable or fails, the rule-based parser answers."""
    return TripDraftRead.model_validate(parse_trip(payload.text, llm_client))
