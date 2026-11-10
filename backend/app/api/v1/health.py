from fastapi import APIRouter

from app.schemas.health import HealthRead

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> HealthRead:
    # TODO(ai): report OllamaClient.is_available() once the AI module is implemented.
    return HealthRead(status="ok", ai_available=False)
