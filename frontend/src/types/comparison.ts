// Mirrors backend/app/schemas/comparison.py - keep both in sync.
// All CO2 and cost values are per person.

import type { TransportMode } from './trip';

export interface ComparisonInput {
  origin: string;
  destination: string;
  passengers: number;
  /** Optional road distance; when set the backend skips geocoding and routing. */
  distance_km?: number;
}

export type RouteSource = 'osrm' | 'estimate' | 'user';

export interface RoutePoint {
  name: string;
  lat: number | null;
  lon: number | null;
}

export interface ComparisonRoute {
  origin: RoutePoint;
  destination: RoutePoint;
  distance_km: number;
  source: RouteSource;
}

export interface ComparisonOption {
  mode: TransportMode;
  distance_km: number;
  duration_min: number;
  cost_pln: number;
  co2_kg: number;
  /** kg CO2 saved vs driving alone in a petrol car; negative means more. */
  co2_saved_vs_car_kg: number;
  practical: boolean;
  note: string | null;
}

export interface ComparisonHighlights {
  greenest: TransportMode | null;
  fastest: TransportMode | null;
  cheapest: TransportMode | null;
}

export interface WeatherInfo {
  location: string;
  temperature_c: number;
  precipitation_mm: number;
  wind_kph: number;
  weather_code: number | null;
  description: string | null;
}

export interface ToolTraceItem {
  tool: string;
  arguments: Record<string, unknown>;
  ok: boolean;
}

/** EcoAdvisor's answer (POST /comparisons/{id}/advice), stored with the comparison. */
export interface Advice {
  recommended_mode: TransportMode;
  summary: string;
  reasons: string[];
  used_llm: boolean;
  model: string | null;
  weather: WeatherInfo | null;
  preferences: string | null;
  tool_trace: ToolTraceItem[];
  created_at: string;
}

/** A stored comparison: the snapshot taken when it was created. */
export interface Comparison {
  id: number;
  created_at: string;
  route: ComparisonRoute;
  passengers: number;
  options: ComparisonOption[];
  highlights: ComparisonHighlights;
  advice: Advice | null;
}

/** Lightweight history row (GET /comparisons). */
export interface ComparisonSummary {
  id: number;
  origin: string;
  destination: string;
  passengers: number;
  distance_km: number;
  created_at: string;
  greenest_mode: TransportMode | null;
  greenest_co2_kg: number | null;
  solo_car_co2_kg: number;
  recommended_mode: TransportMode | null;
}
