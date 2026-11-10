import { useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { Card, CardHeader } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Spinner } from '@/components/Spinner';
import { formatDistance } from '@/lib/format';
import { inputClass } from '@/lib/styles';
import { MODE_LABELS, TRANSPORT_MODES, type TransportMode, type Trip } from '@/types/trip';

import { TripTable } from './TripTable';
import { useTripsQuery } from './useTrips';

interface TripHistoryProps {
  editingId: number | null;
  onEdit: (trip: Trip) => void;
  onDelete: (trip: Trip) => void;
}

function summary(trips: Trip[]): string {
  const totalKm = trips.reduce((sum, trip) => sum + trip.distance_km, 0);
  return `${trips.length} ${trips.length === 1 ? 'trip' : 'trips'} · ${formatDistance(totalKm)}`;
}

export function TripHistory({ editingId, onEdit, onDelete }: TripHistoryProps) {
  const [mode, setMode] = useState<TransportMode | ''>('');
  const { data: trips, isPending, isError, error, refetch } = useTripsQuery(mode || undefined);

  const filter = (
    <>
      <label htmlFor="trip-mode-filter" className="sr-only">
        Filter by transport mode
      </label>
      <select
        id="trip-mode-filter"
        className={`${inputClass()} py-1.5`}
        value={mode}
        onChange={(event) => setMode(event.target.value as TransportMode | '')}
      >
        <option value="">All modes</option>
        {TRANSPORT_MODES.map((value) => (
          <option key={value} value={value}>
            {MODE_LABELS[value]}
          </option>
        ))}
      </select>
    </>
  );

  let content;
  if (isPending) {
    content = (
      <div className="flex justify-center py-14 text-emerald-600">
        <Spinner label="Loading trips…" />
      </div>
    );
  } else if (isError) {
    content = <ErrorState message={getErrorMessage(error)} onRetry={() => void refetch()} />;
  } else if (trips.length === 0) {
    content = mode ? (
      <EmptyState
        title="No trips for this transport mode"
        description="Change the filter or add a new trip."
      />
    ) : (
      <EmptyState
        title="You have no saved trips yet"
        description="Add your first trip using the form. Saved trips will show up here."
      />
    );
  } else {
    content = <TripTable trips={trips} editingId={editingId} onEdit={onEdit} onDelete={onDelete} />;
  }

  return (
    <Card>
      <CardHeader
        title="Trip history"
        description={trips && trips.length > 0 ? summary(trips) : 'Your saved journeys'}
        actions={filter}
      />
      {content}
    </Card>
  );
}
