import type { Advice, Comparison, ComparisonInput, ComparisonSummary } from '@/types/comparison';

import { apiFetch } from './client';

export const comparisonsApi = {
  create: (input: ComparisonInput) =>
    apiFetch<Comparison>('/comparisons', { method: 'POST', body: input }),
  list: (limit: number, offset = 0, signal?: AbortSignal) =>
    apiFetch<ComparisonSummary[]>(`/comparisons?limit=${limit}&offset=${offset}`, { signal }),
  get: (id: number, signal?: AbortSignal) => apiFetch<Comparison>(`/comparisons/${id}`, { signal }),
  remove: (id: number) => apiFetch<void>(`/comparisons/${id}`, { method: 'DELETE' }),
  advise: (id: number, preferences?: string) =>
    apiFetch<Advice>(`/comparisons/${id}/advice`, {
      method: 'POST',
      body: preferences ? { preferences } : {},
    }),
};
