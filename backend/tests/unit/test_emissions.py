import math

import pytest

from app.models.trip import TransportMode
from app.services.emissions import (
    calculate_emissions,
    estimate_cost,
    estimate_duration_min,
    estimate_option,
)
from app.services.transport_factors import FACTORS

ALL_MODES = list(TransportMode)
CAR_MODES = [TransportMode.CAR_PETROL, TransportMode.CAR_EV]
SHARED_MODES = [TransportMode.TRAIN, TransportMode.COACH, TransportMode.PLANE]


def test_every_mode_has_factors() -> None:
    assert set(FACTORS) == set(TransportMode)


@pytest.mark.parametrize("mode", ALL_MODES)
def test_emissions_scale_linearly_with_distance(mode: TransportMode) -> None:
    single = calculate_emissions(100, mode, 1)
    double = calculate_emissions(200, mode, 1)

    assert double == pytest.approx(2 * single)
    assert single == pytest.approx(FACTORS[mode].co2_kg_per_km * 100)


@pytest.mark.parametrize("mode", CAR_MODES)
def test_car_emissions_are_split_between_passengers(mode: TransportMode) -> None:
    alone = calculate_emissions(300, mode, 1)
    four = calculate_emissions(300, mode, 4)

    assert four == pytest.approx(alone / 4)


@pytest.mark.parametrize("mode", SHARED_MODES)
def test_public_transport_emissions_are_per_person(mode: TransportMode) -> None:
    assert calculate_emissions(300, mode, 4) == pytest.approx(calculate_emissions(300, mode, 1))


def test_known_values_per_person() -> None:
    assert calculate_emissions(100, TransportMode.CAR_PETROL, 1) == pytest.approx(16.152)
    assert calculate_emissions(100, TransportMode.TRAIN, 3) == pytest.approx(3.092)
    assert calculate_emissions(100, TransportMode.PLANE, 1) == pytest.approx(22.928)


def test_bike_is_zero_emission_and_free() -> None:
    assert calculate_emissions(20, TransportMode.BIKE, 2) == 0
    assert estimate_cost(20, TransportMode.BIKE, 2) == 0


def test_ev_emits_less_than_petrol_car() -> None:
    assert calculate_emissions(100, TransportMode.CAR_EV) < calculate_emissions(
        100, TransportMode.CAR_PETROL
    )


def test_car_cost_is_split_between_passengers() -> None:
    assert estimate_cost(100, TransportMode.CAR_PETROL, 2) == pytest.approx(
        estimate_cost(100, TransportMode.CAR_PETROL, 1) / 2
    )


@pytest.mark.parametrize(
    ("distance_km", "passengers"),
    [(0, 1), (-10, 1), (math.nan, 1), (math.inf, 1), (100, 0), (100, 10)],
)
def test_invalid_input_raises(distance_km: float, passengers: int) -> None:
    with pytest.raises(ValueError):
        calculate_emissions(distance_km, TransportMode.TRAIN, passengers)


def test_duration_adds_mode_overhead() -> None:
    # 500 km at 500 km/h = 60 min + 120 min airport overhead.
    assert estimate_duration_min(500, TransportMode.PLANE) == 180
    # 90 km at 90 km/h = 60 min + 15 min.
    assert estimate_duration_min(90, TransportMode.TRAIN) == 75


def test_car_duration_prefers_routing_time() -> None:
    assert estimate_duration_min(300, TransportMode.CAR_PETROL, driving_duration_min=200.4) == 200
    # Driving time is ignored for non-car modes.
    assert estimate_duration_min(70, TransportMode.COACH, driving_duration_min=1) == 75


@pytest.mark.parametrize(
    ("mode", "distance_km", "passengers", "practical"),
    [
        (TransportMode.BIKE, 100, 1, True),
        (TransportMode.BIKE, 100.1, 1, False),
        (TransportMode.PLANE, 300, 1, True),
        (TransportMode.PLANE, 299, 1, False),
        (TransportMode.CAR_PETROL, 50, 5, True),
        (TransportMode.CAR_EV, 50, 6, False),
        (TransportMode.TRAIN, 5, 9, True),
    ],
)
def test_practical_boundaries(
    mode: TransportMode, distance_km: float, passengers: int, practical: bool
) -> None:
    option = estimate_option(mode, distance_km, passengers)

    assert option.practical is practical
    assert (option.note is None) is practical


def test_estimate_option_rounds_and_explains() -> None:
    option = estimate_option(TransportMode.BIKE, 400, 1)

    assert option.mode is TransportMode.BIKE
    assert option.distance_km == 400
    assert option.duration_min == 1600
    assert option.co2_kg == 0
    assert option.note == "Too far to cycle (over 100 km)."
