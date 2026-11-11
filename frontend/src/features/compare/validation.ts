import {
  compactErrors,
  FIELD_LIMITS,
  parseDecimal,
  validateDistance,
  validatePassengers,
  localIsoDate,
  validatePlace,
  validateTravelDate,
} from '@/lib/validators';
import type { ComparisonInput } from '@/types/comparison';
import type { TripDraft } from '@/types/tripDraft';

export interface CompareFormValues {
  origin: string;
  destination: string;
  passengers: string;
  /** Optional; empty means "let the backend look up the route". */
  distanceKm: string;
  /** Optional "What matters to you?" text, sent to EcoAdvisor after the comparison. */
  preferences: string;
  /** Day of the (planned) trip, `YYYY-MM-DD`; trips saved from the comparison get it. */
  travelledOn: string;
}

export type CompareFormErrors = Partial<Record<keyof CompareFormValues, string>>;

/** A fresh form; the travel date starts as today. */
export function emptyCompareForm(today: string = localIsoDate()): CompareFormValues {
  return {
    origin: '',
    destination: '',
    passengers: '1',
    distanceKm: '',
    preferences: '',
    travelledOn: today,
  };
}

export function validateCompare(values: CompareFormValues): CompareFormErrors {
  return compactErrors({
    origin: validatePlace(values.origin, 'Enter a starting point.'),
    destination: validatePlace(values.destination, 'Enter a destination.'),
    passengers: validatePassengers(values.passengers),
    distanceKm: values.distanceKm.trim() ? validateDistance(values.distanceKm) : undefined,
    preferences:
      values.preferences.trim().length > FIELD_LIMITS.preferencesMaxLength
        ? `Maximum ${FIELD_LIMITS.preferencesMaxLength} characters.`
        : undefined,
    travelledOn: validateTravelDate(values.travelledOn),
  });
}

/** Form values from a parsed draft. Unknown passengers keep the form's default of 1. */
export function fromTripDraft(draft: TripDraft): CompareFormValues {
  return {
    origin: draft.origin ?? '',
    destination: draft.destination ?? '',
    passengers: String(draft.passengers ?? 1),
    distanceKm: '',
    preferences: draft.preferences ?? '',
    travelledOn: localIsoDate(),
  };
}

/** Preferences for EcoAdvisor, or undefined when the field is empty. */
export function toPreferences(values: CompareFormValues): string | undefined {
  return values.preferences.trim() || undefined;
}

export function toComparisonInput(values: CompareFormValues): ComparisonInput {
  const input: ComparisonInput = {
    origin: values.origin.trim(),
    destination: values.destination.trim(),
    passengers: Number(values.passengers),
    travelled_on: values.travelledOn,
  };
  if (values.distanceKm.trim()) input.distance_km = parseDecimal(values.distanceKm);
  return input;
}
