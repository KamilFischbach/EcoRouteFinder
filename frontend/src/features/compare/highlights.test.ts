import { describe, expect, it } from 'vitest';

import type { ComparisonOption } from '@/types/comparison';
import type { TransportMode } from '@/types/trip';

import { savingsLabel } from './highlights';

function option(mode: TransportMode, saved: number): ComparisonOption {
  return {
    mode,
    distance_km: 300,
    duration_min: 200,
    cost_pln: 90,
    co2_kg: 9.4,
    co2_saved_vs_petrol_car_kg: saved,
    practical: true,
    note: null,
  };
}

describe('savingsLabel', () => {
  it('compares with the same group going by petrol car', () => {
    expect(savingsLabel(option('train', 14.74), 2)).toBe(
      'Saves 14.7 kg CO₂ vs going by petrol car together',
    );
    expect(savingsLabel(option('plane', -34.15), 2)).toBe(
      '34.2 kg CO₂ more vs going by petrol car together',
    );
  });

  it('drops "together" for one traveller', () => {
    expect(savingsLabel(option('train', 38.04), 1)).toBe('Saves 38 kg CO₂ vs going by petrol car');
  });

  it('says when the difference is too small to show', () => {
    expect(savingsLabel(option('car_ev', 0.04), 1)).toBe('Same CO₂ as going by petrol car');
  });

  it('marks the petrol car as the baseline', () => {
    expect(savingsLabel(option('car_petrol', 0), 3)).toBe('Baseline for CO₂ savings');
  });
});
