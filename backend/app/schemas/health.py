from pydantic import BaseModel


class HealthRead(BaseModel):
    status: str
    ai_available: bool
