import type { TripDraft } from '@/types/tripDraft';

import { apiFetch } from './client';

export const tripDraftsApi = {
  create: (text: string) => apiFetch<TripDraft>('/trip-drafts', { method: 'POST', body: { text } }),
};
