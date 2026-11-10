// Mirrors backend/app/schemas/stats.py - keep both in sync.
import type { TransportMode } from './trip';

export const STATS_RANGES = ['30d', '90d', '12m', 'all'] as const;
export type StatsRange = (typeof STATS_RANGES)[number];
export const DEFAULT_STATS_RANGE: StatsRange = '90d';

export type StatsGranularity = 'week' | 'month';

export interface StatsTotals {
  trips: number;
  distance_km: number;
  /** Carbon footprint, kg CO₂ per person. */
  co2_kg: number;
  /** Net kg CO₂ saved per person vs the same group by petrol car; can be negative. */
  co2_saved_kg: number;
  km_not_driven: number;
  eco_points: number;
}

export interface StatsLevel {
  name: string;
  points: number;
  next_level_name: string | null;
  next_level_at: number | null;
  points_to_next: number | null;
  /** 0-1 */
  progress: number;
}

export interface StatsTimelinePoint {
  /** `YYYY-MM-DD`, the first day of the week (Monday) or month. */
  period_start: string;
  co2_kg: number;
  co2_saved_kg: number;
  trips: number;
}

export interface StatsByMode {
  mode: TransportMode;
  trips: number;
  co2_kg: number;
  distance_km: number;
}

export interface StatsPreviousPeriod {
  from: string;
  to: string;
  totals: StatsTotals;
  co2_change_kg: number;
  saved_change_kg: number;
  co2_change_pct: number | null;
  saved_change_pct: number | null;
}

export interface StatsBestTrip {
  id: number | null;
  origin: string;
  destination: string;
  mode: TransportMode;
  travelled_on: string;
  distance_km: number;
  passengers: number;
  co2_kg: number;
  co2_saved_kg: number;
}

export interface Stats {
  range: StatsRange;
  granularity: StatsGranularity;
  from: string;
  to: string;
  totals: StatsTotals;
  level: StatsLevel;
  timeline: StatsTimelinePoint[];
  by_mode: StatsByMode[];
  previous_period: StatsPreviousPeriod | null;
  best_trip: StatsBestTrip | null;
}
