"""Dashboard statistics: carbon footprint over time, CO2 saved and eco-points.

Definitions (keep README "Dashboard" in sync):
- Footprint: the sum of `trip.co2_kg`, which is CO2 **per person**. Old rows without it are
  computed on the fly with `calculate_emissions`.
- Saved: per trip, the petrol car's CO2 for the same distance and the same group (per person)
  minus the trip's CO2. Computed on the fly, never stored. Negative for e.g. flights, and the
  total is **net** (it can be negative too).
- Km not driven: the distance of trips that were not made by petrol car.
- Eco-points and levels: `services/eco_points.py`.

`aggregate_stats` is a pure function (trips + range + today -> frozen dataclasses), so the same
numbers can be served over HTTP now and as an MCP tool later. Values are rounded only in
`_round`, when the result is built. The UI shows these numbers as they are.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum
from typing import Protocol

from app.models.trip import TransportMode, utc_today
from app.services.eco_points import LevelProgress, level_for, trip_points
from app.services.emissions import calculate_emissions


class StatsRange(StrEnum):
    DAYS_30 = "30d"
    DAYS_90 = "90d"
    MONTHS_12 = "12m"
    ALL = "all"


class Granularity(StrEnum):
    WEEK = "week"
    MONTH = "month"


DEFAULT_RANGE = StatsRange.DAYS_90
_RANGE_DAYS = {StatsRange.DAYS_30: 30, StatsRange.DAYS_90: 90}
_GRANULARITY = {
    StatsRange.DAYS_30: Granularity.WEEK,
    StatsRange.DAYS_90: Granularity.WEEK,
    StatsRange.MONTHS_12: Granularity.MONTH,
    StatsRange.ALL: Granularity.MONTH,
}


class TripRecord(Protocol):
    """What the statistics need from a trip. `models.trip.Trip` fits."""

    @property
    def id(self) -> int | None: ...
    @property
    def origin(self) -> str: ...
    @property
    def destination(self) -> str: ...
    @property
    def distance_km(self) -> float: ...
    @property
    def passengers(self) -> int: ...
    @property
    def mode(self) -> TransportMode: ...
    @property
    def co2_kg(self) -> float | None: ...
    @property
    def travelled_on(self) -> date: ...


@dataclass(frozen=True)
class StatsTotals:
    trips: int
    distance_km: float
    co2_kg: float
    co2_saved_kg: float
    km_not_driven: float
    eco_points: int


@dataclass(frozen=True)
class TimelinePoint:
    period_start: date
    co2_kg: float
    co2_saved_kg: float
    trips: int


@dataclass(frozen=True)
class ModeStats:
    mode: TransportMode
    trips: int
    co2_kg: float
    distance_km: float


@dataclass(frozen=True)
class PreviousPeriod:
    date_from: date
    date_to: date
    totals: StatsTotals
    co2_change_kg: float
    """Current minus previous footprint (negative = less CO2 now)."""
    saved_change_kg: float
    co2_change_pct: float | None
    """Footprint change vs the previous period in %, None when the previous footprint was 0."""
    saved_change_pct: float | None


@dataclass(frozen=True)
class BestTrip:
    id: int | None
    origin: str
    destination: str
    mode: TransportMode
    travelled_on: date
    distance_km: float
    passengers: int
    co2_kg: float
    co2_saved_kg: float


@dataclass(frozen=True)
class Stats:
    range: StatsRange
    granularity: Granularity
    date_from: date
    date_to: date
    totals: StatsTotals
    level: LevelProgress
    timeline: list[TimelinePoint]
    by_mode: list[ModeStats]
    previous_period: PreviousPeriod | None
    best_trip: BestTrip | None


@dataclass(frozen=True)
class _Scored:
    """A trip with its CO2 and savings, before rounding."""

    trip: TripRecord
    co2_kg: float
    saved_kg: float


# --- ranges -------------------------------------------------------------------------------------


def period_start(stats_range: StatsRange, today: date, earliest: date | None = None) -> date:
    """First day of the range (inclusive); the range always ends today."""
    if stats_range in _RANGE_DAYS:
        return today - timedelta(days=_RANGE_DAYS[stats_range] - 1)
    if stats_range is StatsRange.MONTHS_12:
        return _add_months(today.replace(day=1), -11)
    return min(earliest, today) if earliest else today


def previous_period_bounds(date_from: date, date_to: date) -> tuple[date, date]:
    """The period of the same number of days that ends the day before `date_from`."""
    length = date_to - date_from
    previous_to = date_from - timedelta(days=1)
    return previous_to - length, previous_to


def fetch_start(stats_range: StatsRange, today: date) -> date | None:
    """Oldest travel date the aggregation needs (incl. the previous period); None = all trips."""
    if stats_range is StatsRange.ALL:
        return None
    return previous_period_bounds(period_start(stats_range, today), today)[0]


def _add_months(day: date, months: int) -> date:
    month_index = day.year * 12 + day.month - 1 + months
    return day.replace(year=month_index // 12, month=month_index % 12 + 1)


def _bucket_start(day: date, granularity: Granularity) -> date:
    if granularity is Granularity.WEEK:
        return day - timedelta(days=day.weekday())  # weeks start on Monday
    return day.replace(day=1)


def _next_bucket(start: date, granularity: Granularity) -> date:
    if granularity is Granularity.WEEK:
        return start + timedelta(days=7)
    return _add_months(start, 1)


# --- aggregation --------------------------------------------------------------------------------


def aggregate_stats(trips: Iterable[TripRecord], stats_range: StatsRange, today: date) -> Stats:
    """Statistics for the trips travelled in `stats_range`, ending `today`. Planned trips (dated
    after `today`) and trips outside the range and its previous period are ignored."""
    scored = [_score(trip) for trip in trips if trip.travelled_on <= today]
    date_to = today
    earliest = min((s.trip.travelled_on for s in scored), default=None)
    date_from = period_start(stats_range, date_to, earliest)
    current = _between(scored, date_from, date_to)
    granularity = _GRANULARITY[stats_range]
    totals = _totals(current)
    return Stats(
        range=stats_range,
        granularity=granularity,
        date_from=date_from,
        date_to=date_to,
        totals=totals,
        level=_rounded_level(level_for(totals.eco_points)),
        timeline=_timeline(current, date_from, date_to, granularity),
        by_mode=_by_mode(current),
        previous_period=(
            None if stats_range is StatsRange.ALL else _previous(scored, date_from, date_to, totals)
        ),
        best_trip=_best_trip(current),
    )


def _score(trip: TripRecord) -> _Scored:
    co2 = trip.co2_kg
    if co2 is None:
        co2 = calculate_emissions(trip.distance_km, trip.mode, trip.passengers)
    baseline = calculate_emissions(trip.distance_km, TransportMode.CAR_PETROL, trip.passengers)
    return _Scored(trip, co2, baseline - co2)


def _between(scored: Sequence[_Scored], start: date, end: date) -> list[_Scored]:
    return [s for s in scored if start <= s.trip.travelled_on <= end]


def _sum(items: Iterable[_Scored], value: Callable[[_Scored], float]) -> float:
    return sum((value(s) for s in items), 0.0)


def _totals(items: Sequence[_Scored]) -> StatsTotals:
    not_driven = [s for s in items if s.trip.mode is not TransportMode.CAR_PETROL]
    return StatsTotals(
        trips=len(items),
        distance_km=_round(_sum(items, lambda s: s.trip.distance_km), 1),
        co2_kg=_round(_sum(items, lambda s: s.co2_kg)),
        co2_saved_kg=_round(_sum(items, lambda s: s.saved_kg)),
        km_not_driven=_round(_sum(not_driven, lambda s: s.trip.distance_km), 1),
        eco_points=sum(trip_points(s.saved_kg) for s in items),
    )


def _timeline(
    items: Sequence[_Scored], date_from: date, date_to: date, granularity: Granularity
) -> list[TimelinePoint]:
    """One point per week or month from `date_from` to `date_to`, empty periods included."""
    buckets: dict[date, list[_Scored]] = {}
    start = _bucket_start(date_from, granularity)
    while start <= date_to:
        buckets[start] = []
        start = _next_bucket(start, granularity)
    for s in items:
        buckets[_bucket_start(s.trip.travelled_on, granularity)].append(s)
    return [
        TimelinePoint(
            period_start=start,
            co2_kg=_round(_sum(group, lambda s: s.co2_kg)),
            co2_saved_kg=_round(_sum(group, lambda s: s.saved_kg)),
            trips=len(group),
        )
        for start, group in buckets.items()
    ]


def _by_mode(items: Sequence[_Scored]) -> list[ModeStats]:
    """Modes that occur, highest footprint first."""
    groups: dict[TransportMode, list[_Scored]] = {}
    for s in items:
        groups.setdefault(s.trip.mode, []).append(s)
    stats = [
        ModeStats(
            mode=mode,
            trips=len(group),
            co2_kg=_round(_sum(group, lambda s: s.co2_kg)),
            distance_km=_round(_sum(group, lambda s: s.trip.distance_km), 1),
        )
        for mode, group in groups.items()
    ]
    return sorted(stats, key=lambda m: (-m.co2_kg, m.mode.value))


def _previous(
    scored: Sequence[_Scored], date_from: date, date_to: date, current: StatsTotals
) -> PreviousPeriod:
    previous_from, previous_to = previous_period_bounds(date_from, date_to)
    totals = _totals(_between(scored, previous_from, previous_to))
    return PreviousPeriod(
        date_from=previous_from,
        date_to=previous_to,
        totals=totals,
        co2_change_kg=_round(current.co2_kg - totals.co2_kg),
        saved_change_kg=_round(current.co2_saved_kg - totals.co2_saved_kg),
        co2_change_pct=_change_pct(current.co2_kg, totals.co2_kg),
        saved_change_pct=_change_pct(current.co2_saved_kg, totals.co2_saved_kg),
    )


def _change_pct(current: float, previous: float) -> float | None:
    """Relative change in %; the sign says up or down even when `previous` is negative."""
    if previous == 0:
        return None
    return _round((current - previous) / abs(previous) * 100, 1)


def _best_trip(items: Sequence[_Scored]) -> BestTrip | None:
    """The trip that saved the most (latest wins a tie); None if no trip saved anything."""
    best = max(items, key=lambda s: (s.saved_kg, s.trip.travelled_on, s.trip.id or 0), default=None)
    if best is None or _round(best.saved_kg) <= 0:
        return None
    trip = best.trip
    return BestTrip(
        id=trip.id,
        origin=trip.origin,
        destination=trip.destination,
        mode=trip.mode,
        travelled_on=trip.travelled_on,
        distance_km=trip.distance_km,
        passengers=trip.passengers,
        co2_kg=_round(best.co2_kg),
        co2_saved_kg=_round(best.saved_kg),
    )


def _rounded_level(level: LevelProgress) -> LevelProgress:
    return replace(level, progress=_round(level.progress, 3))


def _round(value: float, digits: int = 2) -> float:
    """The only rounding of output values. Adding 0.0 turns -0.0 into 0.0."""
    return round(value, digits) + 0.0


# --- use case -----------------------------------------------------------------------------------


class TripSource(Protocol):
    def list_travelled_since(self, start: date | None) -> Sequence[TripRecord]: ...


class StatsService:
    def __init__(self, trips: TripSource) -> None:
        self._trips = trips

    def get_stats(self, stats_range: StatsRange, today: date | None = None) -> Stats:
        day = today or utc_today()
        trips = self._trips.list_travelled_since(fetch_start(stats_range, day))
        return aggregate_stats(trips, stats_range, day)
