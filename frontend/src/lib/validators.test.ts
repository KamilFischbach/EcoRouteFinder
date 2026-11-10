import { describe, expect, it } from 'vitest';

import { localIsoDate, validateTravelDate } from './validators';

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

  it('rejects future dates', () => {
    expect(validateTravelDate('2026-11-11', today)).toBe('The trip date cannot be in the future.');
  });

  it('rejects empty or malformed input', () => {
    expect(validateTravelDate('', today)).toBe('Enter the date of the trip.');
    expect(validateTravelDate('10.11.2026', today)).toBe('Enter the date of the trip.');
  });
});
