const numberFormat = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });
const dateFormat = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

export function formatDistance(km: number): string {
  return `${numberFormat.format(km)} km`;
}

export function formatCo2(kg: number | null): string {
  return kg === null ? '—' : `${numberFormat.format(kg)} kg`;
}

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}
