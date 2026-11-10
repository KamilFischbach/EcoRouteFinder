// Mirrors backend/app/schemas/trip.py - keep both in sync.

export const TRANSPORT_MODES = ['car_petrol', 'car_ev', 'train', 'coach', 'plane', 'bike'] as const;

export type TransportMode = (typeof TRANSPORT_MODES)[number];

export const MODE_LABELS: Record<TransportMode, string> = {
  car_petrol: 'Auto (benzyna)',
  car_ev: 'Auto elektryczne',
  train: 'Pociąg',
  coach: 'Autokar',
  plane: 'Samolot',
  bike: 'Rower',
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
}
