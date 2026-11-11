"""The single place that maps comparisons between dataclasses and the stored record.

Snapshot format (`Comparison.result`), versioned so it can evolve::

    {"version": 2,
     "options": [{"mode": "train", "distance_km": ..., ..., "note": null}, ...],
     "highlights": {"greenest": "train", "fastest": "car_ev", "cheapest": "car_ev"}}
"""

from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from app.models.comparison import Comparison
from app.models.trip import TransportMode
from app.services.comparison_models import (
    ComparedOption,
    ComparedRoute,
    ComparisonResult,
    ComparisonSummary,
    Highlights,
    RoutePoint,
    SavedComparison,
)

# 2: `co2_saved_vs_car_kg` (vs one person driving alone) became `co2_saved_vs_petrol_car_kg`
#    (vs the same group by petrol car). `upgrade_snapshot` converts version 1 exactly, and
#    `app.db.init_db` runs it on old databases at startup.
SNAPSHOT_VERSION = 2


def _mode_or_none(value: Any) -> TransportMode | None:
    return TransportMode(value) if value is not None else None


def petrol_car_co2_kg(snapshot: dict[str, Any]) -> float:
    """The savings baseline: CO2 per person of the petrol car option (same group)."""
    petrol = next(o for o in snapshot["options"] if o["mode"] == TransportMode.CAR_PETROL.value)
    return float(petrol["co2_kg"])


def upgrade_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return `snapshot` in the current format. Version 1 is converted without loss: its petrol
    car option already holds the same group's CO2 per person, the new baseline."""
    if snapshot.get("version") != 1:
        return snapshot
    baseline = petrol_car_co2_kg(snapshot)
    options = []
    for option in snapshot["options"]:
        upgraded = {k: v for k, v in option.items() if k != "co2_saved_vs_car_kg"}
        upgraded["co2_saved_vs_petrol_car_kg"] = round(baseline - option["co2_kg"], 2)
        options.append(upgraded)
    return {**snapshot, "version": SNAPSHOT_VERSION, "options": options}


def to_snapshot(result: ComparisonResult) -> dict[str, Any]:
    return {
        "version": SNAPSHOT_VERSION,
        "options": [{**asdict(o), "mode": o.mode.value} for o in result.options],
        "highlights": {
            name: (mode.value if mode is not None else None)
            for name, mode in asdict(result.highlights).items()
        },
    }


def options_from_snapshot(snapshot: dict[str, Any]) -> list[ComparedOption]:
    return [ComparedOption(**{**o, "mode": TransportMode(o["mode"])}) for o in snapshot["options"]]


def highlights_from_snapshot(snapshot: dict[str, Any]) -> Highlights:
    raw = snapshot["highlights"]
    return Highlights(
        greenest=_mode_or_none(raw["greenest"]),
        fastest=_mode_or_none(raw["fastest"]),
        cheapest=_mode_or_none(raw["cheapest"]),
    )


def to_record(
    result: ComparisonResult,
    origin: str,
    destination: str,
    distance_km: float | None,
    travelled_on: date,
) -> Comparison:
    greenest = result.option(result.highlights.greenest) if result.highlights.greenest else None
    route = result.route
    return Comparison(
        origin=origin,
        destination=destination,
        passengers=result.passengers,
        distance_km=distance_km,
        travelled_on=travelled_on,
        origin_name=route.origin.name,
        origin_lat=route.origin.lat,
        origin_lon=route.origin.lon,
        destination_name=route.destination.name,
        destination_lat=route.destination.lat,
        destination_lon=route.destination.lon,
        road_km=route.distance_km,
        source=route.source,
        result=to_snapshot(result),
        greenest_mode=greenest.mode if greenest else None,
        greenest_co2_kg=greenest.co2_kg if greenest else None,
        petrol_car_co2_kg=result.petrol_car_co2_kg,
    )


def route_from_record(record: Comparison) -> ComparedRoute:
    return ComparedRoute(
        origin=RoutePoint(record.origin_name, record.origin_lat, record.origin_lon),
        destination=RoutePoint(
            record.destination_name, record.destination_lat, record.destination_lon
        ),
        distance_km=record.road_km,
        source=record.source,
    )


def to_saved(record: Comparison) -> SavedComparison:
    if record.id is None:
        raise ValueError("Comparison record has not been saved yet")
    return SavedComparison(
        id=record.id,
        created_at=record.created_at,
        travelled_on=record.travelled_on,
        route=route_from_record(record),
        passengers=record.passengers,
        options=options_from_snapshot(record.result),
        highlights=highlights_from_snapshot(record.result),
        advice=record.advice,
    )


def to_advice_json(answer: Any, created_at: datetime) -> dict[str, Any]:
    """Serialise an AdvisorAnswer (dataclass) to the JSON stored in `Comparison.advice`."""
    data: dict[str, Any] = asdict(answer)
    data["recommended_mode"] = answer.recommended_mode.value
    data["created_at"] = created_at.isoformat()
    return data


def to_summary(record: Comparison) -> ComparisonSummary:
    if record.id is None:
        raise ValueError("Comparison record has not been saved yet")
    return ComparisonSummary(
        id=record.id,
        origin=record.origin_name,
        destination=record.destination_name,
        passengers=record.passengers,
        distance_km=record.road_km,
        created_at=record.created_at,
        travelled_on=record.travelled_on,
        greenest_mode=record.greenest_mode,
        greenest_co2_kg=record.greenest_co2_kg,
        petrol_car_co2_kg=record.petrol_car_co2_kg,
        recommended_mode=record.recommended_mode,
    )
