// Text for the dashboard, built by rules from the numbers the server computed.
// Nothing here recalculates statistics; it only picks words and formats values.
import { formatCo2, formatDay } from '@/lib/format';
import {
  DEFAULT_STATS_RANGE,
  STATS_RANGES,
  type Stats,
  type StatsGranularity,
  type StatsLevel,
  type StatsRange,
} from '@/types/stats';

export const RANGE_LABELS: Record<StatsRange, string> = {
  '30d': '30 days',
  '90d': '90 days',
  '12m': '12 months',
  all: 'All time',
};

/** Reads `?range=`; anything unknown falls back to the default. */
export function parseRange(raw: string | null): StatsRange {
  return STATS_RANGES.find((range) => range === raw) ?? DEFAULT_STATS_RANGE;
}

/** "previous 90 days" */
export function previousPeriodLabel(range: StatsRange): string {
  return `previous ${RANGE_LABELS[range]}`;
}

/** Net savings in words: "38 kg saved vs petrol car" or "12 kg more than going by petrol car". */
export function savedPhrase(savedKg: number): string {
  if (savedKg < 0) return `${formatCo2(Math.abs(savedKg))} more than going by petrol car`;
  return `${formatCo2(savedKg)} saved vs petrol car`;
}

export interface ChangeBadge {
  /** "12%" */
  amount: string;
  direction: 'up' | 'down' | 'same';
  better: boolean | null;
  /** What the change is measured against: "previous 90 days" */
  previous: string;
  /** "12% more than the previous 90 days" */
  description: string;
}

/**
 * Change vs the previous period. `lowerIsBetter` is true for the footprint, false for savings.
 * Returns null when there is nothing to compare with (all time, or a zero previous value).
 */
export function changeBadge(
  pct: number | null | undefined,
  range: StatsRange,
  lowerIsBetter: boolean,
): ChangeBadge | null {
  if (pct === null || pct === undefined) return null;
  const amount = `${Math.abs(pct).toLocaleString('en-GB', { maximumFractionDigits: 1 })}%`;
  const previous = previousPeriodLabel(range);
  if (pct === 0) {
    return {
      amount,
      direction: 'same',
      better: null,
      previous,
      description: `Same as the ${previous}`,
    };
  }
  const direction = pct > 0 ? 'up' : 'down';
  return {
    amount,
    direction,
    better: (direction === 'down') === lowerIsBetter,
    previous,
    description: `${amount} ${direction === 'up' ? 'more' : 'less'} than the ${previous}`,
  };
}

/** One sentence that sums up the period, or null when there are no trips. */
export function summarySentence(stats: Stats): string | null {
  const { totals, previous_period: previous } = stats;
  if (totals.trips === 0) return null;
  if (previous === null) {
    return totals.co2_saved_kg < 0
      ? `Since ${formatDay(stats.from)} your trips emitted ${savedPhrase(totals.co2_saved_kg)}.`
      : `Since ${formatDay(stats.from)} you saved ${formatCo2(totals.co2_saved_kg)} of CO₂ compared with going by petrol car.`;
  }
  const label = previousPeriodLabel(stats.range);
  const change = previous.saved_change_kg;
  if (change === 0) return `You saved as much CO₂ as in the ${label}.`;
  const amount = formatCo2(Math.abs(change));
  return change > 0
    ? `You saved ${amount} more than in the ${label}.`
    : `You saved ${amount} less than in the ${label}.`;
}

/** "835 pts to Tree" or "Top level reached". */
export function nextLevelText(level: StatsLevel): string {
  if (level.next_level_name === null || level.points_to_next === null) {
    return 'Top level reached';
  }
  return `${level.points_to_next.toLocaleString('en-GB')} pts to ${level.next_level_name}`;
}

const weekTick = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
});
const monthTick = new Intl.DateTimeFormat('en-GB', { month: 'short', timeZone: 'UTC' });
const monthLong = new Intl.DateTimeFormat('en-GB', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});

function utcDate(isoDate: string): Date {
  return new Date(`${isoDate}T00:00:00Z`);
}

/** Axis label: weeks "12 Oct", months "Oct". */
export function periodTick(isoDate: string, granularity: StatsGranularity): string {
  return (granularity === 'week' ? weekTick : monthTick).format(utcDate(isoDate));
}

/** Tooltip/table label: "Week of 12 Oct 2026" or "October 2026". */
export function periodLabel(isoDate: string, granularity: StatsGranularity): string {
  return granularity === 'week'
    ? `Week of ${formatDay(isoDate)}`
    : monthLong.format(utcDate(isoDate));
}
