"""Eco-points and levels: a small reward for choosing low-carbon transport.

Rules (keep README "Dashboard" in sync):
- A trip earns `POINTS_PER_KG_SAVED` points for every kg of CO2 it saved per person compared
  with the same group going by petrol car, rounded to a whole number.
- A trip that saved nothing or emitted more than the petrol car (e.g. a flight) earns 0.
  There are no penalties: points only grow.
- Levels are fixed thresholds of the points earned in the chosen range (`LEVELS`). The demo
  data (`python -m app.seed`, about 2,400 points in 90 days) lands in the middle level, Sapling.

Pure functions, no I/O, so they can back an MCP tool later.
"""

from dataclasses import dataclass

POINTS_PER_KG_SAVED = 10


@dataclass(frozen=True)
class Level:
    name: str
    min_points: int


LEVELS: tuple[Level, ...] = (
    Level("Seedling", 0),
    Level("Sprout", 250),
    Level("Sapling", 1500),
    Level("Tree", 4000),
    Level("Forest", 8000),
)


@dataclass(frozen=True)
class LadderStep:
    name: str
    min_points: int
    reached: bool


@dataclass(frozen=True)
class LevelProgress:
    name: str
    points: int
    next_level_name: str | None
    """None on the last level."""
    next_level_at: int | None
    points_to_next: int | None
    progress: float
    """Share of the way from this level's threshold to the next one, 0-1 (1 on the last level)."""
    ladder: tuple[LadderStep, ...]
    """All levels in order, so the UI can show what is reached and what is next."""


def trip_points(co2_saved_kg: float) -> int:
    """Points for one trip. Never negative."""
    return round(max(co2_saved_kg, 0.0) * POINTS_PER_KG_SAVED)


def level_for(points: int) -> LevelProgress:
    """The level reached with `points`; a threshold counts as reached when hit exactly."""
    index = max(i for i, level in enumerate(LEVELS) if points >= level.min_points)
    current = LEVELS[index]
    ladder = tuple(LadderStep(lv.name, lv.min_points, points >= lv.min_points) for lv in LEVELS)
    if index == len(LEVELS) - 1:
        return LevelProgress(current.name, points, None, None, None, 1.0, ladder)
    upcoming = LEVELS[index + 1]
    span = upcoming.min_points - current.min_points
    progress = (points - current.min_points) / span
    return LevelProgress(
        current.name,
        points,
        upcoming.name,
        upcoming.min_points,
        upcoming.min_points - points,
        progress,
        ladder,
    )
