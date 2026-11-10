import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { statsApi } from '@/api/stats';
import type { StatsRange } from '@/types/stats';

export const statsKeys = {
  all: ['stats'] as const,
  detail: (range: StatsRange) => [...statsKeys.all, range] as const,
};

export function useStatsQuery(range: StatsRange) {
  return useQuery({
    queryKey: statsKeys.detail(range),
    queryFn: ({ signal }) => statsApi.get(range, signal),
    // Keep the old numbers on screen while another range loads.
    placeholderData: keepPreviousData,
  });
}
