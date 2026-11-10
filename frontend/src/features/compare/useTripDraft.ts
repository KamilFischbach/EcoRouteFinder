import { useMutation } from '@tanstack/react-query';

import { tripDraftsApi } from '@/api/tripDrafts';

export function useTripDraftMutation() {
  return useMutation({ mutationFn: (text: string) => tripDraftsApi.create(text) });
}
