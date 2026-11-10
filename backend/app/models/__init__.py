"""SQLModel table models. Import every table here so `init_db` can create it."""

from app.models.comparison import Comparison
from app.models.trip import TransportMode, Trip, utc_now

__all__ = ["Comparison", "TransportMode", "Trip", "utc_now"]
