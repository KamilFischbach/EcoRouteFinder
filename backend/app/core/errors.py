"""Domain errors raised by services.

Services raise these instead of HTTP exceptions; the API layer
(`app/api/error_handlers.py`) translates them into HTTP responses.
"""

from typing import Any


class AppError(Exception):
    """Base class for all expected, domain-level errors."""

    code: str = "APP_ERROR"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    """Requested resource does not exist."""

    code = "NOT_FOUND"

    def __init__(self, resource: str, resource_id: int | str) -> None:
        super().__init__(
            f"{resource} with id {resource_id} not found",
            details={"resource": resource, "id": resource_id},
        )
