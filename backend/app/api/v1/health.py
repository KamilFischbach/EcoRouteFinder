from fastapi import APIRouter

from app.ai.llm_client import ai_status
from app.api.deps import LLMClientDep
from app.schemas.health import HealthRead

router = APIRouter(tags=["health"])


@router.get("/health")
def health(llm_client: LLMClientDep) -> HealthRead:
    status = ai_status(llm_client)
    return HealthRead(status="ok", ai_available=status.available, ai_model=status.model)
