import {
  FIELD_LIMITS,
  compactErrors,
  parseDecimal,
  validateDistance,
  validatePassengers,
  validatePlace,
} from '@/lib/validators';
import type { TransportMode, Trip, TripInput } from '@/types/trip';

export { hasErrors } from '@/lib/validators';
export const TRIP_LIMITS = FIELD_LIMITS;

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

export function validateTrip(values: TripFormValues): TripFormErrors {
  return compactErrors({
    origin: validatePlace(values.origin, 'Enter a starting point.'),
    destination: validatePlace(values.destination, 'Enter a destination.'),
    distanceKm: validateDistance(values.distanceKm),
    passengers: validatePassengers(values.passengers),
    mode: values.mode ? undefined : 'Choose a transport mode.',
    note:
      values.note.trim().length > FIELD_LIMITS.noteMaxLength
        ? `Note can be at most ${FIELD_LIMITS.noteMaxLength} characters.`
        : undefined,
  });
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
