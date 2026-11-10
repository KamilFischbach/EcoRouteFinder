import {
  compactErrors,
  parseDecimal,
  validateDistance,
  validatePassengers,
  validatePlace,
} from '@/lib/validators';
import type { ComparisonInput } from '@/types/comparison';
import type { TripDraft } from '@/types/tripDraft';

export interface CompareFormValues {
  origin: string;
  destination: string;
  passengers: string;
  /** Optional; empty means "let the backend look up the route". */
  distanceKm: string;
}

export type CompareFormErrors = Partial<Record<keyof CompareFormValues, string>>;

export const EMPTY_COMPARE_FORM: CompareFormValues = {
  origin: '',
  destination: '',
  passengers: '1',
  distanceKm: '',
};

export function validateCompare(values: CompareFormValues): CompareFormErrors {
  return compactErrors({
    origin: validatePlace(values.origin, 'Enter a starting point.'),
    destination: validatePlace(values.destination, 'Enter a destination.'),
    passengers: validatePassengers(values.passengers),
    distanceKm: values.distanceKm.trim() ? validateDistance(values.distanceKm) : undefined,
  });
}

/** Form values from a parsed draft. Unknown passengers keep the form's default of 1. */
export function fromTripDraft(draft: TripDraft): CompareFormValues {
  return {
    origin: draft.origin ?? '',
    destination: draft.destination ?? '',
    passengers: String(draft.passengers ?? 1),
    distanceKm: '',
  };
}

export function toComparisonInput(values: CompareFormValues): ComparisonInput {
  const input: ComparisonInput = {
    origin: values.origin.trim(),
    destination: values.destination.trim(),
    passengers: Number(values.passengers),
  };
  if (values.distanceKm.trim()) input.distance_km = parseDecimal(values.distanceKm);
  return input;
}
