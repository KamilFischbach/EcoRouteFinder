import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { comparisonsApi } from '@/api/comparisons';
import type { Comparison, ComparisonInput } from '@/types/comparison';

export const RECENT_COMPARISONS_LIMIT = 20;

export const comparisonKeys = {
  all: ['comparisons'] as const,
  lists: () => [...comparisonKeys.all, 'list'] as const,
  list: (limit: number) => [...comparisonKeys.lists(), limit] as const,
  detail: (id: number) => [...comparisonKeys.all, 'detail', id] as const,
};

/** Runs and stores a comparison, then seeds its detail cache and refreshes the history. */
export function useCompareMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ComparisonInput) => comparisonsApi.create(input),
    onSuccess: (comparison) => {
      queryClient.setQueryData(comparisonKeys.detail(comparison.id), comparison);
      return queryClient.invalidateQueries({ queryKey: comparisonKeys.lists() });
    },
  });
}

export function useComparisonsQuery(limit = RECENT_COMPARISONS_LIMIT) {
  return useQuery({
    queryKey: comparisonKeys.list(limit),
    queryFn: ({ signal }) => comparisonsApi.list(limit, 0, signal),
  });
}

/** A stored comparison never changes (except for advice), so it is cached indefinitely. */
export function useComparisonQuery(id: number | undefined) {
  return useQuery({
    queryKey: comparisonKeys.detail(id ?? -1),
    queryFn: ({ signal }) => comparisonsApi.get(id as number, signal),
    enabled: id !== undefined,
    staleTime: Infinity,
  });
}

/** Asks EcoAdvisor and stores the answer in the cached comparison (and its history row). */
export function useAdviceMutation(comparisonId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (preferences: string | undefined) =>
      comparisonsApi.advise(comparisonId, preferences),
    onSuccess: (advice) => {
      queryClient.setQueryData<Comparison>(comparisonKeys.detail(comparisonId), (current) =>
        current ? { ...current, advice } : current,
      );
      return queryClient.invalidateQueries({ queryKey: comparisonKeys.lists() });
    },
  });
}

export function useDeleteComparison() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => comparisonsApi.remove(id),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: comparisonKeys.detail(id) });
      return queryClient.invalidateQueries({ queryKey: comparisonKeys.lists() });
    },
  });
}
