"""Per-mode data used by the emissions, cost and time estimates.

Every number has its source next to it. Values marked "approx." are rough
assumptions, not measured data: treat them as order-of-magnitude, not precise.

CO2 sources:
- DESNZ: UK Government GHG Conversion Factors for Company Reporting 2026
  (flat file, revised July 2026), https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026
  We use direct (tank-to-wheel / in-flight) factors; well-to-tank (WTT) emissions are excluded.
- KOBiZE: "Wskaźniki emisyjności CO2 ... dla energii elektrycznej", December 2025
  (2024 data), CO2 factor for electricity end users: 553 kg CO2/MWh.

Basis: `shared_by_passengers=True` means the CO2 and cost figures are per vehicle-km and are
split between passengers (cars). Otherwise they are per passenger-km (public transport, bike).
"""

from dataclasses import dataclass

from app.models.trip import TransportMode

# DESNZ 2026 "Average car, Battery Electric Vehicle": 0.02686 kg CO2e/km on UK electricity
# at 0.13096 kg CO2e/kWh -> implied consumption 0.02686 / 0.13096 = 0.205 kWh/km.
EV_KWH_PER_KM = 0.205
# KOBiZE, December 2025 (2024 data): 553 kg CO2/MWh for electricity end users in Poland.
PL_GRID_KG_CO2_PER_KWH = 0.553


@dataclass(frozen=True)
class TransportFactors:
    co2_kg_per_km: float
    shared_by_passengers: bool
    cost_pln_per_km: float
    speed_kmh: float
    overhead_min: float
    detour_factor: float
    """Road/track/flight distance divided by great-circle distance."""
    min_practical_km: float | None = None
    max_practical_km: float | None = None
    max_passengers: int | None = None


FACTORS: dict[TransportMode, TransportFactors] = {
    TransportMode.CAR_PETROL: TransportFactors(
        # DESNZ 2026, Passenger vehicles, Cars (by size), Average car, Petrol: 0.16152 kg CO2e/km.
        co2_kg_per_km=0.16152,
        shared_by_passengers=True,
        # approx.: ~7 l/100 km x ~6.5 PLN/l, fuel only (no depreciation, tolls or parking).
        cost_pln_per_km=0.45,
        # approx.: average door-to-door speed, used only when no routing service is available.
        speed_kmh=80,
        overhead_min=0,
        # approx.: typical road-to-great-circle ratio.
        detour_factor=1.25,
        max_passengers=5,
    ),
    TransportMode.CAR_EV: TransportFactors(
        # Derived: EV_KWH_PER_KM x PL_GRID_KG_CO2_PER_KWH = 0.205 x 0.553 = approx. 0.113 kg/km.
        co2_kg_per_km=round(EV_KWH_PER_KM * PL_GRID_KG_CO2_PER_KWH, 3),
        shared_by_passengers=True,
        # approx.: 0.205 kWh/km at ~1.2 PLN/kWh (mix of home and public charging).
        cost_pln_per_km=0.25,
        speed_kmh=80,
        overhead_min=0,
        detour_factor=1.25,
        max_passengers=5,
    ),
    TransportMode.TRAIN: TransportFactors(
        # DESNZ 2026, Business travel - land, Rail, National rail: 0.03092 kg CO2e/passenger-km.
        # UK average used as a proxy for Polish rail (simplification; see DETAILS.md).
        co2_kg_per_km=0.03092,
        shared_by_passengers=False,
        # approx.: typical 2nd-class long-distance ticket price per km.
        cost_pln_per_km=0.30,
        # approx.: average speed including stops.
        speed_kmh=90,
        # approx.: getting to the station and boarding.
        overhead_min=15,
        detour_factor=1.2,
    ),
    TransportMode.COACH: TransportFactors(
        # DESNZ 2026, Business travel - land, Bus, Coach: 0.03948 kg CO2e/passenger-km.
        co2_kg_per_km=0.03948,
        shared_by_passengers=False,
        # approx.: typical long-distance coach fare per km.
        cost_pln_per_km=0.18,
        speed_kmh=70,
        overhead_min=15,
        detour_factor=1.25,
    ),
    TransportMode.PLANE: TransportFactors(
        # DESNZ 2026, Business travel - air, Flights, Domestic, Average passenger, With RF:
        # 0.22928 kg CO2e/passenger-km. Includes radiative forcing (RFI). The domestic factor is
        # used for all flights (simplification: longer flights have lower per-km factors).
        co2_kg_per_km=0.22928,
        shared_by_passengers=False,
        # approx.: short-haul economy fares vary widely.
        cost_pln_per_km=0.80,
        # approx.: block speed of a short flight (taxi, climb, descent included).
        speed_kmh=500,
        # approx.: getting to the airport, security and boarding, plus leaving the airport.
        overhead_min=120,
        # DESNZ applies its air factors to great-circle distance (the 8% routing uplift is
        # understood to be included in the factors), so no extra detour here.
        detour_factor=1.0,
        min_practical_km=300,
    ),
    TransportMode.BIKE: TransportFactors(
        co2_kg_per_km=0.0,
        shared_by_passengers=False,
        cost_pln_per_km=0.0,
        # approx.: leisurely touring pace.
        speed_kmh=15,
        overhead_min=0,
        detour_factor=1.2,
        max_practical_km=100,
    ),
}
