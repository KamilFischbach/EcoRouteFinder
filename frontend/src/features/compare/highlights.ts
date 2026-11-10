import { formatCo2 } from '@/lib/format';
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

/** What savings are compared with: the same group going by petrol car (per person). */
export function petrolCarBaseline(passengers: number): string {
  return passengers === 1 ? 'going by petrol car' : 'going by petrol car together';
}

/** "Saves 14.7 kg CO₂ vs going by petrol car together" / "34.2 kg CO₂ more vs ...". */
export function savingsLabel(option: ComparisonOption, passengers: number): string {
  if (option.mode === 'car_petrol') return 'Baseline for CO₂ savings';
  const saved = option.co2_saved_vs_petrol_car_kg;
  const baseline = petrolCarBaseline(passengers);
  const amount = formatCo2(Math.abs(saved));
  if (amount === formatCo2(0)) return `Same CO₂ as ${baseline}`;
  return saved > 0 ? `Saves ${amount} CO₂ vs ${baseline}` : `${amount} CO₂ more vs ${baseline}`;
}
