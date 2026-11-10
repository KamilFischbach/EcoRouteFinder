"""ComparisonService with a fake RouteProvider (no network)."""

import pytest

from app.core.errors import (
    AppError,
    ExternalServiceError,
    PlaceNotFoundError,
    RouteTooShortError,
)
from app.models.trip import TransportMode
from app.services.comparison_service import ComparisonService, Highlights, pick_highlights
from tests.fakes import FakeRouteProvider, make_route


def test_compare_uses_route_provider_and_returns_every_mode() -> None:
    provider = FakeRouteProvider()
    comparison = ComparisonService(provider).compare("Warszawa", "Kraków", passengers=2)

    assert provider.calls == [("Warszawa", "Kraków")]
    assert comparison.route.source == "osrm"
    assert comparison.route.distance_km == 293.4
    assert comparison.route.origin.lat == pytest.approx(52.2297)
    assert {option.mode for option in comparison.options} == set(TransportMode)


def test_options_are_sorted_by_co2() -> None:
    comparison = ComparisonService(FakeRouteProvider()).compare("Warszawa", "Kraków", 2)

    co2 = [option.co2_kg for option in comparison.options]
    assert co2 == sorted(co2)


def test_mode_distances_road_vs_great_circle() -> None:
    options = {o.mode: o for o in ComparisonService(FakeRouteProvider()).compare("A", "B").options}

    assert options[TransportMode.CAR_PETROL].distance_km == 293.4
    assert options[TransportMode.COACH].distance_km == 293.4
    assert options[TransportMode.TRAIN].distance_km == pytest.approx(252 * 1.2, abs=0.1)
    assert options[TransportMode.PLANE].distance_km == 252


def test_per_person_values_and_savings_vs_driving_alone() -> None:
    options = {
        o.mode: o for o in ComparisonService(FakeRouteProvider()).compare("A", "B", 2).options
    }
    petrol = options[TransportMode.CAR_PETROL]
    train = options[TransportMode.TRAIN]

    # Petrol car shared by 2: 293.4 km x 0.16152 / 2.
    assert petrol.co2_kg == pytest.approx(23.69)
    # Saving vs a solo petrol car (47.39 kg) is the half the passenger no longer emits.
    assert petrol.co2_saved_vs_car_kg == pytest.approx(23.70)
    assert train.co2_kg == pytest.approx(9.35)
    assert train.co2_saved_vs_car_kg == pytest.approx(47.39 - 9.35, abs=0.01)
    assert petrol.duration_min == 180  # OSRM driving time


def test_impractical_options_and_highlights() -> None:
    comparison = ComparisonService(FakeRouteProvider()).compare("A", "B", 2)
    options = {o.mode: o for o in comparison.options}

    assert options[TransportMode.PLANE].practical is False  # 252 km < 300 km
    assert options[TransportMode.BIKE].practical is False  # 302 km > 100 km
    assert options[TransportMode.PLANE].co2_saved_vs_car_kg < 0
    # Bike has zero CO2 but is impractical, so the train is the greenest practical option.
    assert comparison.highlights == Highlights(
        greenest=TransportMode.TRAIN, fastest=TransportMode.CAR_EV, cheapest=TransportMode.CAR_EV
    )


def test_user_distance_skips_the_network() -> None:
    provider = FakeRouteProvider()
    comparison = ComparisonService(provider).compare("Home", "Work", 1, distance_km=12)

    assert provider.calls == []
    assert comparison.route.source == "user"
    assert comparison.route.origin.lat is None
    assert comparison.highlights.greenest is TransportMode.BIKE
    by_mode = {o.mode: o for o in comparison.options}
    assert by_mode[TransportMode.CAR_PETROL].distance_km == 12
    # No driving time without OSRM: 12 km at 80 km/h.
    assert by_mode[TransportMode.CAR_PETROL].duration_min == 9


def test_estimated_route_is_passed_through() -> None:
    provider = FakeRouteProvider(make_route(source="estimate", driving_duration_min=None))

    comparison = ComparisonService(provider).compare("A", "B")

    assert comparison.route.source == "estimate"


def test_route_too_short_raises() -> None:
    provider = FakeRouteProvider(make_route(great_circle_km=0.2, road_km=0.3))

    with pytest.raises(RouteTooShortError):
        ComparisonService(provider).compare("A", "A")


@pytest.mark.parametrize("error", [PlaceNotFoundError("Atlantis"), ExternalServiceError("x")])
def test_provider_errors_propagate(error: AppError) -> None:
    provider = FakeRouteProvider(error=error)

    with pytest.raises(type(error)):
        ComparisonService(provider).compare("A", "Atlantis")


def test_no_practical_options_gives_empty_highlights() -> None:
    assert pick_highlights([]) == Highlights(greenest=None, fastest=None, cheapest=None)
