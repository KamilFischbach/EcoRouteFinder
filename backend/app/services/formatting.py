"""Ready-to-quote strings for numbers shown to users and to the LLM.

One place for display rounding, so reasons, fallback summaries, tool results and the advisor's
context all write the same value the same way ("5 h 54 min", "152 PLN", "15.7 kg"), and the
same way as the UI (`frontend/src/lib/format.ts`). Like `Intl.NumberFormat`, the exact binary
value is rounded half-up: 0.25 kg -> "0.3 kg" (Python's `round` would say 0.2), and 9.35 kg,
stored as 9.3499..., -> "9.3 kg", the same as the UI shows.

Pure functions, no I/O.
"""

from decimal import ROUND_HALF_UP, Decimal


def _half_up(value: float, decimals: int) -> Decimal:
    rounded = Decimal(value).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return abs(rounded) if rounded == 0 else rounded  # never "-0.0"


def format_co2(kg: float) -> str:
    """15.66 -> "15.7 kg" (always one decimal)."""
    return f"{_half_up(kg, 1)} kg"


def format_cost(pln: float) -> str:
    """151.6 -> "152 PLN": estimates aren't precise to the grosz."""
    return f"{_half_up(pln, 0)} PLN"


def format_duration(minutes: float) -> str:
    """354 -> "5 h 54 min", 180 -> "3 h", 40 -> "40 min"."""
    total = int(_half_up(minutes, 0))
    hours, mins = divmod(total, 60)
    if hours == 0:
        return f"{mins} min"
    return f"{hours} h" if mins == 0 else f"{hours} h {mins} min"


def format_distance(km: float) -> str:
    """293.44 -> "293.4 km", 12.0 -> "12 km"."""
    text = f"{_half_up(km, 1)}"
    return f"{text.removesuffix('.0')} km"


def format_temperature(celsius: float) -> str:
    """-0.4 -> "0 °C", 2.5 -> "3 °C"."""
    return f"{_half_up(celsius, 0)} °C"


def format_co2_saving(saved_kg: float) -> str:
    """CO₂ saved compared with a baseline: "14.3 kg less", "7.0 kg more" or "no difference"."""
    text = format_co2(abs(saved_kg))
    if text == format_co2(0):
        return "no difference"
    return f"{text} {'less' if saved_kg > 0 else 'more'}"
