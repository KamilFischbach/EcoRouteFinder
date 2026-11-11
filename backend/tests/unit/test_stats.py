from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import pytest

from app.models.trip import TransportMode
from app.services.eco_points import level_for, trip_points
from app.services.emissions import calculate_emissions
from app.services.stats import (
    Granularity,
    StatsRange,
    StatsService,
    TripRecord,
    aggregate_stats,
    fetch_start,
)

TODAY = date(2026, 11, 10)  # a Tuesday
M = TransportMode


@dataclass(frozen=True)
class FakeTrip:
    travelled_on: date
    mode: TransportMode = M.TRAIN
    distance_km: float = 100.0
    passengers: int = 1
    co2_kg: float | None = None
    id: int | None = 1
    origin: str = "Warszawa"
    destination: str = "Łódź"


def co2(mode: TransportMode, km: float = 100.0, people: int = 1) -> float:
    return calculate_emissions(km, mode, people)


def saved(mode: TransportMode, km: float = 100.0, people: int = 1) -> float:
    return co2(M.CAR_PETROL, km, people) - co2(mode, km, people)


def stats_for(trips: Sequence[FakeTrip], stats_range: StatsRange = StatsRange.DAYS_30):
    return aggregate_stats(trips, stats_range, TODAY)


# --- empty / one trip ---------------------------------------------------------------------------


def test_no_trips_gives_zeros_and_a_continuous_timeline() -> None:
    stats = stats_for([], StatsRange.DAYS_90)

    assert stats.totals.trips == 0
    assert stats.totals.co2_kg == 0 and stats.totals.co2_saved_kg == 0
    assert stats.totals.eco_points == 0
    assert stats.level.name == "Seedling" and stats.level.progress == 0
    assert stats.by_mode == [] and stats.best_trip is None
    assert stats.granularity is Granularity.WEEK
    assert len(stats.timeline) == 14  # 90 days touch 14 Monday-weeks
    assert all(p.trips == 0 and p.co2_kg == 0 for p in stats.timeline)
    assert stats.previous_period is not None
    assert stats.previous_period.co2_change_pct is None
    assert stats.previous_period.saved_change_pct is None


def test_one_train_trip() -> None:
    stats = stats_for([FakeTrip(date(2026, 11, 2), co2_kg=round(co2(M.TRAIN), 2))])

    totals = stats.totals
    assert totals.trips == 1
    assert totals.distance_km == 100
    assert totals.co2_kg == round(co2(M.TRAIN), 2)
    assert totals.co2_saved_kg == pytest.approx(saved(M.TRAIN), abs=0.01)
    assert totals.km_not_driven == 100
    assert totals.eco_points == trip_points(saved(M.TRAIN)) > 0
    assert [(m.mode, m.trips) for m in stats.by_mode] == [(M.TRAIN, 1)]
    assert stats.best_trip is not None and stats.best_trip.mode is M.TRAIN


def test_missing_co2_is_computed_on_the_fly() -> None:
    stats = stats_for([FakeTrip(date(2026, 11, 2), mode=M.COACH, co2_kg=None)])

    assert stats.totals.co2_kg == round(co2(M.COACH), 2)


# --- ranges and periods -------------------------------------------------------------------------


def test_30_days_include_both_ends_and_fill_empty_weeks() -> None:
    trips = [
        FakeTrip(date(2026, 10, 11)),  # one day too old
        FakeTrip(date(2026, 10, 12)),  # first day of the range
        FakeTrip(date(2026, 10, 18)),  # Sunday: still the week of 12 Oct
        FakeTrip(date(2026, 10, 19)),  # Monday: next week
        FakeTrip(TODAY),
    ]

    stats = stats_for(trips)

    assert (stats.date_from, stats.date_to) == (date(2026, 10, 12), TODAY)
    assert stats.totals.trips == 4
    assert [(p.period_start, p.trips) for p in stats.timeline] == [
        (date(2026, 10, 12), 2),
        (date(2026, 10, 19), 1),
        (date(2026, 10, 26), 0),
        (date(2026, 11, 2), 0),
        (date(2026, 11, 9), 1),
    ]


def test_12_months_use_calendar_months() -> None:
    trips = [FakeTrip(date(2025, 11, 30)), FakeTrip(date(2025, 12, 1)), FakeTrip(date(2026, 3, 31))]

    stats = stats_for(trips, StatsRange.MONTHS_12)

    assert stats.granularity is Granularity.MONTH
    assert stats.date_from == date(2025, 12, 1)
    assert len(stats.timeline) == 12
    assert stats.timeline[0].period_start == date(2025, 12, 1)
    assert stats.timeline[-1].period_start == date(2026, 11, 1)
    assert stats.totals.trips == 2
    assert {p.period_start: p.trips for p in stats.timeline}[date(2026, 3, 1)] == 1


def test_all_time_starts_at_the_first_trip_and_has_no_previous_period() -> None:
    stats = stats_for([FakeTrip(date(2024, 5, 20)), FakeTrip(TODAY)], StatsRange.ALL)

    assert stats.date_from == date(2024, 5, 20)
    assert stats.timeline[0].period_start == date(2024, 5, 1)
    assert len(stats.timeline) == 31
    assert stats.totals.trips == 2
    assert stats.previous_period is None


def test_all_time_without_trips_is_just_today() -> None:
    stats = stats_for([], StatsRange.ALL)

    assert stats.date_from == stats.date_to == TODAY
    assert [p.period_start for p in stats.timeline] == [date(2026, 11, 1)]


def test_planned_trips_are_not_counted_yet() -> None:
    planned = FakeTrip(date(2026, 11, 14), id=2)

    stats = stats_for([FakeTrip(TODAY, id=1), planned], StatsRange.ALL)

    assert stats.date_to == TODAY
    assert stats.totals.trips == 1
    assert stats.best_trip is not None and stats.best_trip.id == 1


def test_previous_period_has_the_same_length_and_compares_totals() -> None:
    previous = FakeTrip(date(2026, 9, 12), co2_kg=10.0)  # first day of the previous 30 days
    too_old = FakeTrip(date(2026, 9, 11), co2_kg=99.0)
    current = FakeTrip(date(2026, 11, 1), co2_kg=15.0)

    stats = stats_for([too_old, previous, current])

    period = stats.previous_period
    assert period is not None
    assert (period.date_from, period.date_to) == (date(2026, 9, 12), date(2026, 10, 11))
    assert period.totals.trips == 1 and period.totals.co2_kg == 10.0
    assert period.co2_change_pct == 50.0
    assert period.co2_change_kg == 5.0


def test_fetch_start_covers_the_previous_period() -> None:
    assert fetch_start(StatsRange.DAYS_30, TODAY) == date(2026, 9, 12)
    assert fetch_start(StatsRange.ALL, TODAY) is None


# --- savings, points and levels -----------------------------------------------------------------


def test_baseline_is_the_same_group_by_petrol_car_per_person() -> None:
    stats = stats_for([FakeTrip(TODAY, mode=M.CAR_EV, passengers=2)])

    assert stats.totals.co2_saved_kg == pytest.approx(saved(M.CAR_EV, people=2), abs=0.01)
    assert stats.totals.co2_saved_kg < saved(M.CAR_EV, people=1)


def test_petrol_car_saves_nothing_and_is_not_counted_as_km_not_driven() -> None:
    stats = stats_for([FakeTrip(TODAY, mode=M.CAR_PETROL, co2_kg=round(co2(M.CAR_PETROL), 2))])

    assert stats.totals.co2_saved_kg == 0.0
    assert stats.totals.km_not_driven == 0
    assert stats.totals.eco_points == 0
    assert stats.best_trip is None


def test_flight_saving_is_negative_and_the_total_is_net_without_point_penalties() -> None:
    flight = FakeTrip(TODAY, mode=M.PLANE, distance_km=500, id=1)
    train = FakeTrip(TODAY, mode=M.TRAIN, distance_km=100, id=2)

    stats = stats_for([flight, train])

    net = saved(M.PLANE, 500) + saved(M.TRAIN, 100)
    assert saved(M.PLANE, 500) < 0
    assert stats.totals.co2_saved_kg == pytest.approx(net, abs=0.01)
    assert stats.totals.eco_points == trip_points(saved(M.TRAIN, 100))
    assert stats.best_trip is not None and stats.best_trip.id == 2


def test_only_a_flight_has_no_best_trip_and_zero_points() -> None:
    stats = stats_for([FakeTrip(TODAY, mode=M.PLANE, distance_km=500)])

    assert stats.totals.co2_saved_kg < 0
    assert stats.totals.eco_points == 0
    assert stats.best_trip is None


def test_best_trip_is_the_one_that_saved_most() -> None:
    trips = [
        FakeTrip(TODAY, mode=M.BIKE, distance_km=20, id=1),
        FakeTrip(TODAY, mode=M.TRAIN, distance_km=400, passengers=2, id=2),
        FakeTrip(TODAY, mode=M.COACH, distance_km=100, id=3),
    ]

    best = stats_for(trips).best_trip

    assert best is not None
    assert best.id == 2
    assert best.co2_saved_kg == pytest.approx(saved(M.TRAIN, 400, 2), abs=0.01)


def test_by_mode_lists_only_used_modes_highest_footprint_first() -> None:
    trips = [
        FakeTrip(TODAY, mode=M.BIKE),
        FakeTrip(TODAY, mode=M.CAR_PETROL),
        FakeTrip(TODAY, mode=M.CAR_PETROL),
    ]

    by_mode = stats_for(trips).by_mode

    assert [(m.mode, m.trips, m.distance_km) for m in by_mode] == [
        (M.CAR_PETROL, 2, 200),
        (M.BIKE, 1, 100),
    ]


def test_trip_points_are_ten_per_kg_and_never_negative() -> None:
    assert trip_points(3.26) == 33
    assert trip_points(0) == 0
    assert trip_points(-25) == 0


@pytest.mark.parametrize(
    ("points", "name", "next_name", "progress"),
    [
        (0, "Seedling", "Sprout", 0.0),
        (249, "Seedling", "Sprout", 0.996),
        (250, "Sprout", "Sapling", 0.0),
        (2750, "Sapling", "Tree", 0.5),
        (7999, "Tree", "Forest", 0.99975),
        (8000, "Forest", None, 1.0),
    ],
)
def test_levels_reach_a_threshold_exactly_on_it(
    points: int, name: str, next_name: str | None, progress: float
) -> None:
    level = level_for(points)

    assert (level.name, level.next_level_name) == (name, next_name)
    assert level.progress == pytest.approx(progress)


def test_last_level_has_no_next_threshold() -> None:
    assert level_for(20_000).next_level_at is None
    assert level_for(20_000).points_to_next is None
    assert level_for(1000).points_to_next == 500
    assert [step.reached for step in level_for(1500).ladder] == [True, True, True, False, False]


# --- service ------------------------------------------------------------------------------------


class FakeTripSource:
    def __init__(self, trips: Sequence[TripRecord]) -> None:
        self.trips = trips
        self.starts: list[date | None] = []

    def list_travelled_since(self, start: date | None) -> Sequence[TripRecord]:
        self.starts.append(start)
        return self.trips


def test_service_asks_for_trips_once_from_the_previous_period() -> None:
    source = FakeTripSource([FakeTrip(TODAY)])

    stats = StatsService(source).get_stats(StatsRange.DAYS_90, today=TODAY)

    assert source.starts == [date(2026, 5, 15)]
    assert stats.totals.trips == 1
