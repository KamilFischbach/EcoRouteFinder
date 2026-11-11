// Shared field validators. Limits mirror backend/app/schemas/trip.py (PlaceName, DistanceKm, Passengers).

export const FIELD_LIMITS = {
  placeMaxLength: 120,
  noteMaxLength: 500,
  maxDistanceKm: 40_000,
  minPassengers: 1,
  maxPassengers: 9,
  // GET /comparisons: limit 1..100 (backend/app/api/v1/comparisons.py).
  maxHistoryPageSize: 100,
  // AdviceCreate.preferences and TripDraftCreate.text (backend/app/schemas).
  preferencesMaxLength: 300,
  tripDescriptionMaxLength: 500,
  // Planned trips: at most this many days ahead (TravelDate in backend/app/schemas/trip.py).
  maxDaysAhead: 366,
} as const;

/** Today's date in the user's time zone as `YYYY-MM-DD` (the format of `<input type="date">`). */
export function localIsoDate(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

/** `YYYY-MM-DD` plus `days`, without time zone surprises. */
export function addDays(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** The latest allowed travel date: planned trips may be up to a year ahead. */
export function latestTravelDate(today: string = localIsoDate()): string {
  return addDays(today, FIELD_LIMITS.maxDaysAhead);
}

/** Mirrors `TravelDate` in backend/app/schemas/trip.py: a real date, at most a year ahead. */
export function validateTravelDate(
  raw: string,
  today: string = localIsoDate(),
): string | undefined {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw) || Number.isNaN(Date.parse(raw))) {
    return 'Enter the date of the trip.';
  }
  if (raw > latestTravelDate(today)) return 'The trip date can be at most a year ahead.';
  return undefined;
}

/** Accepts both "12.5" and "12,5". */
export function parseDecimal(raw: string): number {
  return Number(raw.trim().replace(',', '.'));
}

export function validatePlace(value: string, emptyMessage: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return emptyMessage;
  if (trimmed.length > FIELD_LIMITS.placeMaxLength) {
    return `Maximum ${FIELD_LIMITS.placeMaxLength} characters.`;
  }
  return undefined;
}

export function validateDistance(raw: string): string | undefined {
  if (!raw.trim()) return 'Enter a distance.';
  const distance = parseDecimal(raw);
  if (!Number.isFinite(distance) || distance <= 0) {
    return 'Distance must be a number greater than 0.';
  }
  if (distance > FIELD_LIMITS.maxDistanceKm) return 'Distance cannot exceed 40,000 km.';
  return undefined;
}

export function validatePassengers(raw: string): string | undefined {
  const passengers = Number(raw);
  const { minPassengers, maxPassengers } = FIELD_LIMITS;
  if (
    !raw.trim() ||
    !Number.isInteger(passengers) ||
    passengers < minPassengers ||
    passengers > maxPassengers
  ) {
    return `Passengers must be a whole number from ${minPassengers} to ${maxPassengers}.`;
  }
  return undefined;
}

/** Drops fields without an error so `Object.keys(errors).length` means "has errors". */
export function compactErrors<T extends Record<string, string | undefined>>(
  errors: T,
): Partial<Record<keyof T, string>> {
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  ) as Partial<Record<keyof T, string>>;
}

export function hasErrors(errors: object): boolean {
  return Object.keys(errors).length > 0;
}
