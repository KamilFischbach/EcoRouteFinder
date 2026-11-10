import type { Stats, StatsRange } from '@/types/stats';

import { apiFetch } from './client';

export const statsApi = {
  get: (range: StatsRange, signal?: AbortSignal) =>
    apiFetch<Stats>(`/stats?range=${encodeURIComponent(range)}`, { signal }),
};
