import type { TransportMode, Trip, TripInput } from '@/types/trip';

// Limits mirror backend/app/schemas/trip.py.
export const TRIP_LIMITS = {
  placeMaxLength: 120,
  noteMaxLength: 500,
  maxDistanceKm: 40_000,
  minPassengers: 1,
  maxPassengers: 9,
} as const;

/** Raw form state: inputs hold strings until the form is submitted. */
export interface TripFormValues {
  origin: string;
  destination: string;
  distanceKm: string;
  passengers: string;
  mode: TransportMode | '';
  note: string;
}

export type TripFormErrors = Partial<Record<keyof TripFormValues, string>>;

export const EMPTY_TRIP_FORM: TripFormValues = {
  origin: '',
  destination: '',
  distanceKm: '',
  passengers: '1',
  mode: '',
  note: '',
};

/** Accepts both "12.5" and "12,5". */
function parseDecimal(raw: string): number {
  return Number(raw.trim().replace(',', '.'));
}

function validatePlace(value: string, emptyMessage: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return emptyMessage;
  if (trimmed.length > TRIP_LIMITS.placeMaxLength) {
    return `Maksymalnie ${TRIP_LIMITS.placeMaxLength} znaków.`;
  }
  return undefined;
}

function validateDistance(raw: string): string | undefined {
  if (!raw.trim()) return 'Podaj dystans.';
  const distance = parseDecimal(raw);
  if (!Number.isFinite(distance) || distance <= 0) return 'Dystans musi być liczbą większą od 0.';
  if (distance > TRIP_LIMITS.maxDistanceKm) return 'Dystans nie może przekraczać 40 000 km.';
  return undefined;
}

function validatePassengers(raw: string): string | undefined {
  const passengers = Number(raw);
  const { minPassengers, maxPassengers } = TRIP_LIMITS;
  if (
    !raw.trim() ||
    !Number.isInteger(passengers) ||
    passengers < minPassengers ||
    passengers > maxPassengers
  ) {
    return `Liczba osób musi być liczbą całkowitą od ${minPassengers} do ${maxPassengers}.`;
  }
  return undefined;
}

export function validateTrip(values: TripFormValues): TripFormErrors {
  const errors: TripFormErrors = {
    origin: validatePlace(values.origin, 'Podaj miejsce startu.'),
    destination: validatePlace(values.destination, 'Podaj cel podróży.'),
    distanceKm: validateDistance(values.distanceKm),
    passengers: validatePassengers(values.passengers),
    mode: values.mode ? undefined : 'Wybierz środek transportu.',
    note:
      values.note.trim().length > TRIP_LIMITS.noteMaxLength
        ? `Notatka może mieć maksymalnie ${TRIP_LIMITS.noteMaxLength} znaków.`
        : undefined,
  };
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  ) as TripFormErrors;
}

export function hasErrors(errors: TripFormErrors): boolean {
  return Object.keys(errors).length > 0;
}

/** Converts validated form values to the API payload. */
export function toTripInput(values: TripFormValues): TripInput {
  if (!values.mode) throw new Error('toTripInput called with invalid values');
  return {
    origin: values.origin.trim(),
    destination: values.destination.trim(),
    distance_km: parseDecimal(values.distanceKm),
    passengers: Number(values.passengers),
    mode: values.mode,
    note: values.note.trim() || null,
  };
}

export function toFormValues(trip: Trip): TripFormValues {
  return {
    origin: trip.origin,
    destination: trip.destination,
    distanceKm: String(trip.distance_km),
    passengers: String(trip.passengers),
    mode: trip.mode,
    note: trip.note ?? '',
  };
}
