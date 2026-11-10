"""Application settings loaded from environment variables and an optional `.env` file."""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Env var names are the upper-cased field names."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "EcoRoute API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./ecoroute.db"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    # Local LLM via Ollama. Without a running Ollama the app uses rule-based fallbacks.
    ai_enabled: bool = True
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    # A 7B model on CPU can take a while per call.
    ollama_timeout_s: float = 90.0
    ollama_temperature: float = 0.2
    # Routing: OpenStreetMap Nominatim (geocoding) + OSRM (driving routes).
    geocoder_url: str = "https://nominatim.openstreetmap.org"
    routing_url: str = "https://router.project-osrm.org"
    http_timeout_s: float = 8.0
    # Nominatim's usage policy requires an identifying User-Agent.
    http_user_agent: str = "EcoRoute/0.1 (+https://github.com/KamilFischbach/EcoRouteFinder)"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string (``a,b``) as well as a list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
