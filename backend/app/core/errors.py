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


class PlaceNotFoundError(AppError):
    """A place name could not be geocoded."""

    code = "UNKNOWN_PLACE"

    def __init__(self, place: str) -> None:
        super().__init__(f"Could not find a place called '{place}'", details={"place": place})


class RouteTooShortError(AppError):
    """Origin and destination are (practically) the same point."""

    code = "ROUTE_TOO_SHORT"

    def __init__(self, distance_km: float) -> None:
        super().__init__(
            "Origin and destination are too close to compare travel options",
            details={"distance_km": round(distance_km, 3)},
        )


class ExternalServiceError(AppError):
    """A required external service (e.g. the geocoder) is unavailable."""

    code = "SERVICE_UNAVAILABLE"

    def __init__(self, service: str) -> None:
        super().__init__(
            f"The {service} service is unavailable. Please try again later.",
            details={"service": service},
        )
