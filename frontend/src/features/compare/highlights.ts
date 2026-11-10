import type { ComparisonHighlights, ComparisonOption } from '@/types/comparison';
import type { TransportMode } from '@/types/trip';

export type Highlight = 'Greenest' | 'Fastest' | 'Cheapest';

export function highlightsFor(mode: TransportMode, highlights: ComparisonHighlights): Highlight[] {
  const result: Highlight[] = [];
  if (highlights.greenest === mode) result.push('Greenest');
  if (highlights.fastest === mode) result.push('Fastest');
  if (highlights.cheapest === mode) result.push('Cheapest');
  return result;
}

/** Practical options first, each group ordered by CO2 per person (lowest first). */
export function sortOptions(options: ComparisonOption[]): ComparisonOption[] {
  return [...options].sort(
    (a, b) => Number(b.practical) - Number(a.practical) || a.co2_kg - b.co2_kg,
  );
}

/** "38.9 kg CO₂ less than driving alone" / "10 kg CO₂ more ..." / "Same as driving alone". */
export function savingsLabel(savedKg: number): string {
  const rounded = Math.round(Math.abs(savedKg) * 10) / 10;
  if (rounded === 0) return 'Same CO₂ as driving alone';
  const direction = savedKg > 0 ? 'less' : 'more';
  return `${rounded.toLocaleString('en-GB')} kg CO₂ ${direction} than driving alone`;
}
