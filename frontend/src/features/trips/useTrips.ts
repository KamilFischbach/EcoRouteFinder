import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { tripsApi } from '@/api/trips';
import { statsKeys } from '@/features/dashboard/useStats';
import type { TransportMode, TripInput } from '@/types/trip';

export const tripKeys = {
  all: ['trips'] as const,
  list: (mode?: TransportMode) => [...tripKeys.all, 'list', mode ?? 'all'] as const,
};

export function useTripsQuery(mode?: TransportMode) {
  return useQuery({
    queryKey: tripKeys.list(mode),
    queryFn: ({ signal }) => tripsApi.list(mode, signal),
  });
}

/** Trips feed the dashboard statistics, so both are refreshed after a change. */
function useInvalidateTrips() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: tripKeys.all }),
      queryClient.invalidateQueries({ queryKey: statsKeys.all }),
    ]);
}

export function useCreateTrip() {
  const invalidate = useInvalidateTrips();
  return useMutation({
    mutationFn: (input: TripInput) => tripsApi.create(input),
    onSuccess: invalidate,
  });
}

export function useUpdateTrip() {
  const invalidate = useInvalidateTrips();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: TripInput }) => tripsApi.update(id, input),
    onSuccess: invalidate,
  });
}

export function useDeleteTrip() {
  const invalidate = useInvalidateTrips();
  return useMutation({
    mutationFn: (id: number) => tripsApi.remove(id),
    onSuccess: invalidate,
  });
}
