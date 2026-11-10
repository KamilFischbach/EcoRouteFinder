import { describe, expect, it } from 'vitest';

import { formatDuration, formatRelativeTime } from './format';

describe('formatRelativeTime', () => {
  const now = Date.parse('2026-11-10T12:00:00Z');

  it.each([
    ['2026-11-10T11:59:40Z', 'just now'],
    ['2026-11-10T11:55:00Z', '5 min ago'],
    ['2026-11-10T10:00:00Z', '2 h ago'],
    ['2026-11-07T12:00:00Z', '3 d ago'],
    ['2026-10-01T12:00:00Z', '1 Oct 2026'],
  ])('%s -> %s', (iso, expected) => {
    expect(formatRelativeTime(iso, now)).toBe(expected);
  });
});

describe('formatDuration', () => {
  it.each([
    [40, '40 min'],
    [60, '1 h'],
    [95, '1 h 35 min'],
  ])('%i -> %s', (minutes, expected) => {
    expect(formatDuration(minutes)).toBe(expected);
  });
});
