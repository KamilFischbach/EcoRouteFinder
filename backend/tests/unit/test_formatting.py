"""Ready-to-quote number strings: deterministic, half-up, the same as the UI."""

import pytest

from app.services.formatting import (
    format_co2,
    format_co2_saving,
    format_cost,
    format_distance,
    format_duration,
    format_temperature,
)


@pytest.mark.parametrize(
    ("kg", "text"),
    [
        (15.66, "15.7 kg"),
        (15.7, "15.7 kg"),
        (0.0, "0.0 kg"),
        (0.25, "0.3 kg"),  # exact .5 rounds up (Python's round() would give 0.2)
        (9.35, "9.3 kg"),  # stored as 9.3499..., like Intl.NumberFormat in the UI
        (-0.04, "0.0 kg"),  # never "-0.0"
        (123.456, "123.5 kg"),
    ],
)
def test_format_co2(kg: float, text: str) -> None:
    assert format_co2(kg) == text


@pytest.mark.parametrize(
    ("pln", "text"),
    [(151.6, "152 PLN"), (90.72, "91 PLN"), (52.5, "53 PLN"), (0.4, "0 PLN"), (36.67, "37 PLN")],
)
def test_format_cost(pln: float, text: str) -> None:
    assert format_cost(pln) == text


@pytest.mark.parametrize(
    ("minutes", "text"),
    [
        (354, "5 h 54 min"),
        (180, "3 h"),
        (65, "1 h 5 min"),
        (40, "40 min"),
        (0, "0 min"),
        (59.5, "1 h"),  # rounds before splitting into hours
    ],
)
def test_format_duration(minutes: float, text: str) -> None:
    assert format_duration(minutes) == text


@pytest.mark.parametrize(
    ("km", "text"),
    [(293.44, "293.4 km"), (12.0, "12 km"), (12.04, "12 km"), (0.96, "1 km"), (0.95, "0.9 km")],
)
def test_format_distance(km: float, text: str) -> None:
    assert format_distance(km) == text


@pytest.mark.parametrize(("celsius", "text"), [(2.5, "3 °C"), (-0.4, "0 °C"), (-3.6, "-4 °C")])
def test_format_temperature(celsius: float, text: str) -> None:
    assert format_temperature(celsius) == text


@pytest.mark.parametrize(
    ("saved", "text"),
    [
        (14.34, "14.3 kg less"),
        (-34.09, "34.1 kg more"),
        (0.0, "no difference"),
        (0.04, "no difference"),  # below what one decimal can show
        (-0.04, "no difference"),
    ],
)
def test_format_co2_saving(saved: float, text: str) -> None:
    assert format_co2_saving(saved) == text
