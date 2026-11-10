import { useMutation } from '@tanstack/react-query';

import { comparisonsApi } from '@/api/comparisons';
import type { ComparisonInput } from '@/types/comparison';

/** A comparison is computed on demand and not cached: it is a POST that stores nothing. */
export function useCompareMutation() {
  return useMutation({
    mutationFn: (input: ComparisonInput) => comparisonsApi.create(input),
  });
}
