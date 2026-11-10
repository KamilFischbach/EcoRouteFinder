import type { Comparison, ComparisonInput } from '@/types/comparison';

import { apiFetch } from './client';

export const comparisonsApi = {
  create: (input: ComparisonInput) =>
    apiFetch<Comparison>('/comparisons', { method: 'POST', body: input }),
};
