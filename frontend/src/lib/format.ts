const numberFormat = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });
const moneyFormat = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});
const dateFormat = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });
const dayFormat = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' });

export function formatDistance(km: number): string {
  return `${numberFormat.format(km)} km`;
}

export function formatCo2(kg: number | null): string {
  return kg === null ? '—' : `${numberFormat.format(kg)} kg`;
}

/** Formats a calendar date (`YYYY-MM-DD`) without shifting it across time zones. */
export function formatDay(isoDate: string): string {
  return dayFormat.format(new Date(`${isoDate}T00:00:00Z`));
}

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

/** Approximate cost, rounded to whole złoty (estimates aren't precise to the grosz). */
export function formatCost(pln: number): string {
  return `${moneyFormat.format(pln)} PLN`;
}

/** "just now", "5 min ago", "2 h ago", "3 d ago", then a date. */
export function formatRelativeTime(iso: string, now: number = Date.now()): string {
  const minutes = Math.floor((now - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} d ago`;
  return formatDate(iso);
}

/** 95 -> "1 h 35 min", 40 -> "40 min". */
export function formatDuration(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = Math.round(totalMinutes % 60);
  if (hours === 0) return `${minutes} min`;
  return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`;
}
