const numberFormat = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });
const moneyFormat = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});
const dayFormat = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' });

export function formatDistance(km: number): string {
  return `${numberFormat.format(km)} km`;
}

export function formatCo2(kg: number | null): string {
  return kg === null ? '—' : `${numberFormat.format(kg)} kg`;
}

/** Formats a calendar date (`YYYY-MM-DD`) without shifting it across time zones. */
/** Chart value label: numbers as "9.4 kg", anything else as nothing. */
export function formatCo2Label(value: unknown): string {
  return typeof value === 'number' ? formatCo2(value) : '';
}

export function formatDay(isoDate: string): string {
  return dayFormat.format(new Date(`${isoDate}T00:00:00Z`));
}

/** Approximate cost, rounded to whole złoty (estimates aren't precise to the grosz). */
export function formatCost(pln: number): string {
  return `${moneyFormat.format(pln)} PLN`;
}

/** 95 -> "1 h 35 min", 40 -> "40 min". */
export function formatDuration(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = Math.round(totalMinutes % 60);
  if (hours === 0) return `${minutes} min`;
  return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`;
}
