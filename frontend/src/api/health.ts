import type { Health } from '@/types/health';

import { apiFetch } from './client';

export const healthApi = {
  get: (signal?: AbortSignal) => apiFetch<Health>('/health', { signal }),
};
