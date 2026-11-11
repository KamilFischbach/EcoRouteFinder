import { describe, expect, it } from 'vitest';

import { addDays, latestTravelDate, localIsoDate, validateTravelDate } from './validators';

describe('localIsoDate', () => {
  it('uses the local calendar day with zero padding', () => {
    expect(localIsoDate(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05');
  });
});

describe('validateTravelDate', () => {
  const today = '2026-11-10';

  it('accepts today and past dates', () => {
    expect(validateTravelDate(today, today)).toBeUndefined();
    expect(validateTravelDate('2025-02-28', today)).toBeUndefined();
  });

  it('accepts planned dates up to a year ahead and rejects later ones', () => {
    expect(validateTravelDate('2026-11-15', today)).toBeUndefined();
    expect(validateTravelDate(latestTravelDate(today), today)).toBeUndefined();
    expect(validateTravelDate('2027-11-12', today)).toBe(
      'The trip date can be at most a year ahead.',
    );
  });

  it('adds days across months and years', () => {
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
    expect(latestTravelDate('2026-11-10')).toBe('2027-11-11');
  });

  it('rejects empty or malformed input', () => {
    expect(validateTravelDate('', today)).toBe('Enter the date of the trip.');
    expect(validateTravelDate('10.11.2026', today)).toBe('Enter the date of the trip.');
  });
});
