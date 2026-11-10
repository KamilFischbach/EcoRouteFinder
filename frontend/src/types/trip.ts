// Mirrors backend/app/schemas/trip.py - keep both in sync.

export const TRANSPORT_MODES = ['car_petrol', 'car_ev', 'train', 'coach', 'plane', 'bike'] as const;

export type TransportMode = (typeof TRANSPORT_MODES)[number];

export const MODE_LABELS: Record<TransportMode, string> = {
  car_petrol: 'Petrol car',
  car_ev: 'Electric car',
  train: 'Train',
  coach: 'Coach',
  plane: 'Plane',
  bike: 'Bike',
};

export interface Trip {
  id: number;
  origin: string;
  destination: string;
  distance_km: number;
  passengers: number;
  mode: TransportMode;
  co2_kg: number | null;
  note: string | null;
  /** Day of the journey, `YYYY-MM-DD`. */
  travelled_on: string;
  created_at: string;
  updated_at: string;
}

/** Payload for creating or updating a trip. */
export interface TripInput {
  origin: string;
  destination: string;
  distance_km: number;
  passengers: number;
  mode: TransportMode;
  note: string | null;
  /** `YYYY-MM-DD`; cannot be in the future. */
  travelled_on: string;
}
