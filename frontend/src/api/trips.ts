import type { TransportMode, Trip, TripInput } from '@/types/trip';

import { apiFetch } from './client';

export const tripsApi = {
  list: (mode?: TransportMode, signal?: AbortSignal) =>
    apiFetch<Trip[]>(mode ? `/trips?mode=${encodeURIComponent(mode)}` : '/trips', { signal }),
  get: (id: number) => apiFetch<Trip>(`/trips/${id}`),
  create: (input: TripInput) => apiFetch<Trip>('/trips', { method: 'POST', body: input }),
  update: (id: number, input: Partial<TripInput>) =>
    apiFetch<Trip>(`/trips/${id}`, { method: 'PUT', body: input }),
  remove: (id: number) => apiFetch<void>(`/trips/${id}`, { method: 'DELETE' }),
};
