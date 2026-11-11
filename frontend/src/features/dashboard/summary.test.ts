import { describe, expect, it } from 'vitest';

import { statsFixture } from '@/test/handlers';
import type { Stats } from '@/types/stats';

import {
  changeBadge,
  nextLevelText,
  parseRange,
  periodLabel,
  periodTick,
  savedPhrase,
  summarySentence,
} from './summary';

function withPrevious(savedChangeKg: number): Stats {
  return {
    ...statsFixture,
    previous_period: { ...statsFixture.previous_period!, saved_change_kg: savedChangeKg },
  };
}

describe('parseRange', () => {
  it('accepts known ranges and falls back to 90 days', () => {
    expect(parseRange('12m')).toBe('12m');
    expect(parseRange(null)).toBe('90d');
    expect(parseRange('7d')).toBe('90d');
  });
});

describe('savedPhrase', () => {
  it('names net savings and net extra emissions honestly', () => {
    expect(savedPhrase(38.04)).toBe('38 kg saved vs petrol car');
    expect(savedPhrase(-12)).toBe('12 kg more than going by petrol car');
  });
});

describe('changeBadge', () => {
  it('treats a lower footprint as better', () => {
    expect(changeBadge(-10, '90d', true)).toEqual({
      amount: '10%',
      direction: 'down',
      better: true,
      description: '10% less than the previous 90 days',
    });
  });

  it('treats higher savings as better and more emissions as worse', () => {
    expect(changeBadge(33.3, '30d', false)?.better).toBe(true);
    expect(changeBadge(5, '30d', true)?.better).toBe(false);
  });

  it('has nothing to show without a comparison', () => {
    expect(changeBadge(null, '90d', true)).toBeNull();
    expect(changeBadge(undefined, 'all', true)).toBeNull();
  });
});

describe('summarySentence', () => {
  it('compares savings with the previous period', () => {
    expect(summarySentence(withPrevious(38))).toBe(
      'You saved 38 kg more than in the previous 90 days.',
    );
    expect(summarySentence(withPrevious(-4.5))).toBe(
      'You saved 4.5 kg less than in the previous 90 days.',
    );
    expect(summarySentence(withPrevious(0))).toBe(
      'You saved as much CO₂ as in the previous 90 days.',
    );
  });

  it('describes all time without a previous period', () => {
    const allTime: Stats = { ...statsFixture, range: 'all', previous_period: null };
    expect(summarySentence(allTime)).toBe(
      'Since 13 Aug 2026 you saved 152.2 kg of CO₂ compared with going by petrol car.',
    );
    const negative = { ...allTime, totals: { ...allTime.totals, co2_saved_kg: -12 } };
    expect(summarySentence(negative)).toBe(
      'Since 13 Aug 2026 your trips emitted 12 kg more than going by petrol car.',
    );
  });

  it('says nothing without trips', () => {
    expect(summarySentence({ ...statsFixture, totals: { ...statsFixture.totals, trips: 0 } })).toBe(
      null,
    );
  });
});

describe('nextLevelText', () => {
  it('shows the points left or the top level', () => {
    expect(nextLevelText(statsFixture.level)).toBe('1,634 pts to Tree');
    expect(
      nextLevelText({
        name: 'Forest',
        points: 9000,
        next_level_name: null,
        next_level_at: null,
        points_to_next: null,
        progress: 1,
        ladder: [],
      }),
    ).toBe('Top level reached');
  });
});

describe('period labels', () => {
  it('labels weeks by day and months by name', () => {
    expect(periodTick('2026-10-12', 'week')).toBe('12 Oct');
    expect(periodTick('2026-10-01', 'month')).toBe('Oct');
    expect(periodLabel('2026-10-12', 'week')).toBe('Week of 12 Oct 2026');
    expect(periodLabel('2026-10-01', 'month')).toBe('October 2026');
  });
});
