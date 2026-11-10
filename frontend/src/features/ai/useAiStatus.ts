import { useQuery } from '@tanstack/react-query';

import { healthApi } from '@/api/health';

export const healthKeys = { all: ['health'] as const };

/** Polls /health once a minute (the backend caches the Ollama check for ~30 s). */
export function useHealthQuery() {
  return useQuery({
    queryKey: healthKeys.all,
    queryFn: ({ signal }) => healthApi.get(signal),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}
