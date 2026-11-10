"""Deterministic facts for EcoAdvisor answers, and a check of the model's summary against them.

- `suitable_options`: practical options minus the bike when luggage or the weather rule it out.
- `build_reasons`: every reason shown to the user, numbers and "cheapest/fastest/lowest CO₂"
  labels included, generated from the comparison. The LLM never writes reasons.
- `check_summary`: the LLM only writes a short summary. Superlatives ("cheapest", "one of the
  fastest", "greenest"), comparatives ("cheaper than the train") and numbers in it must match
  the data, otherwise `SummaryMismatchError` is raised and the advisor falls back to rules.

Plain functions, no FastAPI, no LLM calls.
"""

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.ai.tools import comparison_to_tool_data
from app.models.trip import TransportMode
from app.services.comparison_models import ComparedOption, ComparisonResult
from app.services.formatting import (
    format_co2,
    format_co2_saving,
    format_cost,
    format_duration,
    format_temperature,
)
from app.services.weather import WeatherInfo, bad_for_cycling

M = TransportMode

MODE_LABELS: dict[TransportMode, str] = {
    M.CAR_PETROL: "Petrol car",
    M.CAR_EV: "Electric car",
    M.TRAIN: "Train",
    M.COACH: "Coach",
    M.PLANE: "Plane",
    M.BIKE: "Bike",
}

# Preference keywords (English + Polish stems).
CHEAP_WORDS = ("cheap", "budget", "low cost", "tani", "tanio", "najtan")
FAST_WORDS = ("fast", "quick", "hurry", "asap", "szybk", "najszyb")
LUGGAGE_WORDS = ("luggage", "suitcase", "bags", "baggage", "bagaż", "walizk")
COMFORT_WORDS = ("comfort", "comfy", "relax", "wygod", "komfort")
# Things that don't fit on a bike and are awkward in a coach's hold.
BULKY_WORDS = (
    "ski", "snowboard", "equipment", "gear", "bulky", "large suitcase", "big suitcase",
    "with my bike", "with a bike", "with our bikes", "with bikes",
    "nart", "narciar", "sprzęt", "duża walizk", "dużą walizk", "duże walizk", "z rower",
)  # fmt: skip
# From this road distance on, a coach is ranked behind the train for comfort or bulky equipment.
LONG_TRIP_KM = 200.0


class SummaryMismatchError(Exception):
    """The model's summary says something the data does not support."""


# --- wording --------------------------------------------------------------------------


def petrol_car_baseline(passengers: int) -> str:
    """What CO₂ savings are compared with: the same group going by petrol car."""
    return "going by petrol car" if passengers == 1 else "going by petrol car together"


def savings(option: ComparedOption, passengers: int) -> str | None:
    """ "14.3 kg less than going by petrol car together"; None for the petrol car itself."""
    if option.mode is M.CAR_PETROL:
        return None
    saving = format_co2_saving(option.co2_saved_vs_petrol_car_kg)
    baseline = petrol_car_baseline(passengers)
    if saving == "no difference":
        return f"the same as {baseline}"
    return f"{saving} than {baseline}"


def co2_line(option: ComparedOption, passengers: int) -> str:
    """ "9.3 kg CO₂ per person, 14.3 kg less than going by petrol car together" """
    saving = savings(option, passengers)
    return f"{format_co2(option.co2_kg)} CO₂ per person" + (f", {saving}" if saving else "")


def mentions(text: str | None, words: tuple[str, ...]) -> bool:
    """True when a word of `text` starts with one of `words` ("ski" matches "skiing", not
    "asking")."""
    pattern = r"\b(?:" + "|".join(re.escape(word) for word in words) + ")"
    return re.search(pattern, (text or "").lower()) is not None


def special_needs(preferences: str | None) -> str | None:
    """What the trip has to suit besides CO₂, e.g. "bulky equipment and a comfortable trip"."""
    needs = []
    if mentions(preferences, BULKY_WORDS):
        needs.append("bulky equipment")
    if mentions(preferences, COMFORT_WORDS):
        needs.append("a comfortable trip")
    return " and ".join(needs) or None


# --- suitable options and reasons -----------------------------------------------------


@dataclass(frozen=True)
class Suitable:
    options: list[ComparedOption]
    notes: list[str]
    """Why options were skipped, e.g. "Bike skipped because you mentioned luggage."."""
    narrowed: bool
    """True when something was skipped, so "of the practical options" would be wrong."""


def _bike_skip_reason(preferences: str | None, weather: WeatherInfo | None) -> str | None:
    if mentions(preferences, LUGGAGE_WORDS):
        return "you mentioned luggage"
    if mentions(preferences, BULKY_WORDS):
        return "you have bulky equipment"
    if mentions(preferences, COMFORT_WORDS):
        return "comfort matters to you"
    weather_problem = bad_for_cycling(weather) if weather else None
    return f"of {weather_problem}" if weather_problem else None


def _coach_skip_reason(
    comparison: ComparisonResult, preferences: str | None, modes: set[TransportMode]
) -> str | None:
    """On long trips the train beats the coach for comfort and for bulky equipment."""
    if comparison.route.distance_km < LONG_TRIP_KM or not {M.TRAIN, M.COACH} <= modes:
        return None
    if mentions(preferences, BULKY_WORDS):
        return "the train is easier with bulky equipment"
    if mentions(preferences, COMFORT_WORDS):
        return "the train is more comfortable"
    return None


def suitable_options(
    comparison: ComparisonResult, preferences: str | None, weather: WeatherInfo | None
) -> Suitable:
    practical = [o for o in comparison.options if o.practical] or list(comparison.options)
    options, notes = list(practical), []
    bike_reason = _bike_skip_reason(preferences, weather)
    if bike_reason and any(o.mode is M.BIKE for o in options):
        options = [o for o in options if o.mode is not M.BIKE]
        notes.append(f"Bike skipped because {bike_reason}.")
    coach_reason = _coach_skip_reason(comparison, preferences, {o.mode for o in options})
    if coach_reason:
        options = [o for o in options if o.mode is not M.COACH]
        notes.append(f"Coach skipped: on a trip over {LONG_TRIP_KM:.0f} km {coach_reason}.")
    if not options:
        return Suitable(practical, notes, narrowed=False)
    return Suitable(options, notes, narrowed=len(options) < len(practical))


Metric = Literal["cost", "time", "co2"]
METRICS: tuple[Metric, ...] = ("co2", "time", "cost")


def metric_value(option: ComparedOption, metric: Metric) -> float:
    if metric == "cost":
        return option.cost_pln
    if metric == "time":
        return float(option.duration_min)
    return option.co2_kg


_EPS = 1e-6


def is_best(option: ComparedOption, options: list[ComparedOption], metric: Metric) -> bool:
    """Lowest value of `metric` among `options` (ties count as best)."""
    return metric_value(option, metric) <= min(metric_value(o, metric) for o in options) + _EPS


def best_option(options: list[ComparedOption], metric: Metric) -> ComparedOption:
    second: Metric = "time" if metric == "co2" else "co2"
    return min(options, key=lambda o: (metric_value(o, metric), metric_value(o, second)))


_RANK_WORDS: dict[Metric, str] = {"co2": "lowest CO₂", "time": "fastest", "cost": "cheapest"}


def build_reasons(
    pick: TransportMode,
    comparison: ComparisonResult,
    preferences: str | None,
    weather: WeatherInfo | None,
) -> list[str]:
    """All reasons for recommending `pick`, generated from the data (never by the LLM)."""
    option = comparison.option(pick)
    if option is None:
        raise ValueError(f"{pick} is not part of this comparison")
    suitable = suitable_options(comparison, preferences, weather)

    reasons = [
        f"{co2_line(option, comparison.passengers)}.",
        f"About {format_duration(option.duration_min)} door to door, roughly "
        f"{format_cost(option.cost_pln)} per person.",
        *suitable.notes,
    ]

    pool = suitable.options
    if option in pool and len(pool) > 1:
        ranks = [_RANK_WORDS[m] for m in METRICS if is_best(option, pool, m)]
        if ranks:
            group = "remaining options" if suitable.narrowed else "practical options"
            text = " and ".join(ranks)
            reasons.append(f"{text[0].upper()}{text[1:]} of the {group}.")
        if mentions(preferences, CHEAP_WORDS) and not is_best(option, pool, "cost"):
            other = best_option(pool, "cost")
            reasons.append(
                f"Not the cheapest: {MODE_LABELS[other.mode]} costs about "
                f"{format_cost(other.cost_pln)} per person."
            )
        elif mentions(preferences, FAST_WORDS) and not is_best(option, pool, "time"):
            other = best_option(pool, "time")
            reasons.append(
                f"Not the fastest: {MODE_LABELS[other.mode]} takes about "
                f"{format_duration(other.duration_min)}."
            )

    weather_problem = bad_for_cycling(weather) if weather else None
    if weather and not weather_problem:
        reasons.append(
            f"Weather in {weather.location}: {format_temperature(weather.temperature_c)}, "
            f"{weather.description or 'no rain'}."
        )
    return reasons


# --- summary check: modes, claims and numbers -----------------------------------------

# Longest aliases first, so "electric car" wins over "car". Polish stems take any ending.
_MODE_ALIASES: list[tuple[str, TransportMode]] = [
    (r"electric cars?|e-?cars?|evs?|elektryk\w*|samoch[oó]d\w* elektryczn\w*", M.CAR_EV),
    (r"auto\w* elektryczn\w*", M.CAR_EV),
    (r"petrol cars?|cars?|samoch[oó]d\w*|auto|autem", M.CAR_PETROL),
    (r"trains?|rail|pociąg\w*|kolej\w*", M.TRAIN),
    (r"coach(?:es)?|bus(?:es)?|autobus\w*|autokar\w*", M.COACH),
    (r"planes?|flights?|flying|fly|samolot\w*", M.PLANE),
    (r"bikes?|bicycles?|cycling|cycle|rower\w*", M.BIKE),
]
_MODE_RE = re.compile(
    "|".join(f"(?P<m{i}>\\b(?:{pattern})\\b)" for i, (pattern, _) in enumerate(_MODE_ALIASES)),
    re.IGNORECASE,
)

_CO2 = r"(?:co2|co₂|emissions?|carbon|emisj\w*)"
# (regex, metric, direction): direction "low" = cheapest/fastest/greenest, "high" = the opposite.
_SUPERLATIVES: list[tuple[str, Metric, str]] = [
    (r"cheapest|least expensive|lowest (?:cost|price|fare)|najtańsz\w*", "cost", "low"),
    (r"most expensive|priciest|highest (?:cost|price)|najdroższ\w*", "cost", "high"),
    (r"fastest|quickest|shortest (?:travel |journey |trip )?time|najszybsz\w*", "time", "low"),
    (r"slowest|najwolniejsz\w*", "time", "high"),
    (
        rf"greenest|cleanest|most (?:eco[- ]?friendly|sustainable|environmentally friendly)"
        rf"|lowest {_CO2}|least {_CO2}|least polluting|najbardziej ekologiczn\w*"
        rf"|najczystsz\w*|najekologiczniejsz\w*|najniższ\w* {_CO2}",
        "co2",
        "low",
    ),
    (rf"highest {_CO2}|most {_CO2}|most polluting|dirtiest|najwyższ\w* {_CO2}", "co2", "high"),
]
_COMPARATIVES: list[tuple[str, Metric, str]] = [
    (r"cheaper|less expensive|(?<!naj)tańsz\w*", "cost", "low"),
    (r"more expensive|pricier|(?<!naj)droższ\w*", "cost", "high"),
    (r"faster|quicker|(?<!naj)szybsz\w*", "time", "low"),
    (r"slower|(?<!naj)wolniejsz\w*", "time", "high"),
    (
        rf"greener|cleaner|less {_CO2}|lower {_CO2}|fewer {_CO2}|(?<!naj)czystsz\w*"
        rf"|bardziej ekologiczn\w*|ekologiczniejsz\w*",
        "co2",
        "low",
    ),
    (rf"more {_CO2}|higher {_CO2}|more polluting|dirtier", "co2", "high"),
]


def _compile(patterns: list[tuple[str, Metric, str]]) -> list[tuple[re.Pattern[str], Metric, str]]:
    return [(re.compile(rf"\b(?:{p})\b", re.IGNORECASE), m, d) for p, m, d in patterns]


_SUPERLATIVE_RES = _compile(_SUPERLATIVES)
_COMPARATIVE_RES = _compile(_COMPARATIVES)
_WEAK_RE = re.compile(r"\b(?:one of the|among the|jed\w* z)\s+$", re.IGNORECASE)
_NEGATION_RE = re.compile(
    r"\b(?:not|isn't|aren't|never|no longer|nie)\b(?:\W+\w+)?\W*$", re.IGNORECASE
)
_OBJECT_MARKER_RE = re.compile(
    r"\b(?:than|compared (?:to|with)|unlike|versus|vs\.?|niż|od|w porównaniu z)\W*(?:\w+\W+)?$",
    re.IGNORECASE,
)
_CLAUSE_SPLIT_RE = re.compile(
    r"[.;!?]+\s|[.;!?]+$|\s(?:but|while|whereas|although|though|however|ale|lecz|choć)\s",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _Mention:
    start: int
    end: int
    mode: TransportMode


def _mode_mentions(clause: str) -> list[_Mention]:
    found = []
    for match in _MODE_RE.finditer(clause):
        index = int(next(k for k, v in match.groupdict().items() if v is not None)[1:])
        found.append(_Mention(match.start(), match.end(), _MODE_ALIASES[index][1]))
    return found


def _subject(
    clause: str, mentions_: list[_Mention], at: int, fallback: TransportMode
) -> TransportMode:
    """The mode a claim at position `at` is about: nearest mention before it, else the first
    mention after it that isn't the other side of a comparison, else the recommended mode."""
    before = [m for m in mentions_ if m.end <= at]
    if before:
        return before[-1].mode
    for m in mentions_:
        if m.start >= at and not _OBJECT_MARKER_RE.search(clause[: m.start]):
            return m.mode
    return fallback


def _ranks_ok(
    option: ComparedOption, pools: list[list[ComparedOption]], metric: Metric, sign: int, weak: bool
) -> bool:
    """True when `option` is the best (weak: in the better half) of at least one pool."""
    for pool in pools:
        if option not in pool:
            continue
        value = sign * metric_value(option, metric)
        better = sum(1 for o in pool if sign * metric_value(o, metric) < value - _EPS)
        limit = math.ceil(len(pool) / 2) - 1 if weak else 0
        if better <= limit:
            return True
    return False


def find_false_claims(
    summary: str,
    recommended: TransportMode,
    comparison: ComparisonResult,
    preferences: str | None,
    weather: WeatherInfo | None,
) -> list[str]:
    """Superlative and comparative claims in `summary` that the data contradicts."""
    practical = [o for o in comparison.options if o.practical]
    pools = [
        suitable_options(comparison, preferences, weather).options,
        practical,
        list(comparison.options),
    ]
    problems: list[str] = []
    for clause in _CLAUSE_SPLIT_RE.split(summary):
        found = _mode_mentions(clause)
        for regex, metric, direction in _SUPERLATIVE_RES:
            for match in regex.finditer(clause):
                head = clause[: match.start()]
                if _NEGATION_RE.search(head):
                    continue
                mode = _subject(clause, found, match.start(), recommended)
                option = comparison.option(mode)
                sign = 1 if direction == "low" else -1
                weak = bool(_WEAK_RE.search(head))
                if option is not None and not _ranks_ok(option, pools, metric, sign, weak):
                    problems.append(f"{mode.value} is not '{match.group(0)}'")
        for regex, metric, direction in _COMPARATIVE_RES:
            for match in regex.finditer(clause):
                if _NEGATION_RE.search(clause[: match.start()]):
                    continue
                after = [m for m in found if m.start >= match.end()]
                if not after:
                    continue  # "cheaper than going by car": no single mode to compare with
                subject = _subject(clause, found, match.start(), recommended)
                left, right = comparison.option(subject), comparison.option(after[0].mode)
                if left is None or right is None or left is right:
                    continue
                sign = 1 if direction == "low" else -1
                if not sign * metric_value(left, metric) < sign * metric_value(right, metric):
                    problems.append(
                        f"{subject.value} is not '{match.group(0)}' than {after[0].mode.value}"
                    )
    return problems


# --- numbers --------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?")
_IGNORED_RE = re.compile(r"co2|co₂|\b[a-z]+\d[\w.:-]*", re.IGNORECASE)  # "CO2", "qwen3:8b"


def _numbers_in(text: str) -> list[str]:
    return _NUMBER_RE.findall(_IGNORED_RE.sub(" ", text))


def _walk(value: Any, key: str = "") -> Iterator[float]:
    if isinstance(value, bool):
        return
    if isinstance(value, int | float):
        yield abs(float(value))
        if key.endswith("_min"):  # durations may be written as "3 h 37 min" or "3.6 hours"
            hours, mins = divmod(int(value), 60)
            yield from (float(hours), float(mins), value / 60)
    elif isinstance(value, str):
        yield from (float(n.replace(",", ".")) for n in _numbers_in(value))
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, str(k))
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _walk(item, key)


def known_numbers(
    comparison: ComparisonResult,
    weather: WeatherInfo | None,
    preferences: str | None,
    reasons: list[str],
    tool_data: Iterable[Any] = (),
) -> list[float]:
    """Every number the model was shown (context, tool calls and results) or will be shown
    next to its summary (the reasons)."""
    sources: list[Any] = [
        comparison_to_tool_data(comparison),
        asdict(weather) if weather else None,
        preferences or "",
        reasons,
        *tool_data,
    ]
    return sorted(set(_walk(sources)))


def find_unknown_numbers(summary: str, known: list[float]) -> list[str]:
    """Numbers in `summary` that don't match a known value at the precision they are written."""
    unknown = []
    for raw in _numbers_in(summary):
        text = raw.replace(",", ".")
        decimals = len(text.split(".")[1]) if "." in text else 0
        tolerance = 0.5 * 10**-decimals + _EPS
        if not any(abs(float(text) - value) <= tolerance for value in known):
            unknown.append(raw)
    return unknown


def check_summary(
    summary: str,
    recommended: TransportMode,
    comparison: ComparisonResult,
    preferences: str | None,
    weather: WeatherInfo | None,
    reasons: list[str],
    tool_data: Iterable[Any] = (),
) -> None:
    """Raise `SummaryMismatchError` when the summary contradicts the data or invents a number."""
    claims = find_false_claims(summary, recommended, comparison, preferences, weather)
    if claims:
        raise SummaryMismatchError("False claim: " + "; ".join(claims))
    known = known_numbers(comparison, weather, preferences, reasons, tool_data)
    numbers = find_unknown_numbers(summary, known)
    if numbers:
        raise SummaryMismatchError("Numbers not in the data: " + ", ".join(numbers))
