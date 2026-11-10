from pydantic import BaseModel


class HealthRead(BaseModel):
    status: str
    ai_available: bool
    """True when Ollama answers and the configured model is pulled (cached ~30 s)."""
    ai_model: str | None
    """Configured model name, or None when AI is disabled."""
