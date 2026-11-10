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

function pluralizeTrips(count: number): string {
  if (count === 1) return 'trasa';
  const lastDigit = count % 10;
  const lastTwoDigits = count % 100;
  const isFew = lastDigit >= 2 && lastDigit <= 4 && (lastTwoDigits < 12 || lastTwoDigits > 14);
  return isFew ? 'trasy' : 'tras';
}

function summary(trips: Trip[]): string {
  const totalKm = trips.reduce((sum, trip) => sum + trip.distance_km, 0);
  return `${trips.length} ${pluralizeTrips(trips.length)} · ${formatDistance(totalKm)}`;
}

export function TripHistory({ editingId, onEdit, onDelete }: TripHistoryProps) {
  const [mode, setMode] = useState<TransportMode | ''>('');
  const { data: trips, isPending, isError, error, refetch } = useTripsQuery(mode || undefined);

  const filter = (
    <>
      <label htmlFor="trip-mode-filter" className="sr-only">
        Filtruj po środku transportu
      </label>
      <select
        id="trip-mode-filter"
        className={`${inputClass()} py-1.5`}
        value={mode}
        onChange={(event) => setMode(event.target.value as TransportMode | '')}
      >
        <option value="">Wszystkie środki</option>
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
        <Spinner label="Ładowanie tras…" />
      </div>
    );
  } else if (isError) {
    content = <ErrorState message={getErrorMessage(error)} onRetry={() => void refetch()} />;
  } else if (trips.length === 0) {
    content = mode ? (
      <EmptyState
        title="Brak tras dla tego środka transportu"
        description="Zmień filtr albo dodaj nową trasę."
      />
    ) : (
      <EmptyState
        title="Nie masz jeszcze zapisanych tras"
        description="Dodaj pierwszą trasę w formularzu obok. Zapisane trasy pojawią się tutaj."
      />
    );
  } else {
    content = <TripTable trips={trips} editingId={editingId} onEdit={onEdit} onDelete={onDelete} />;
  }

  return (
    <Card>
      <CardHeader
        title="Historia tras"
        description={trips && trips.length > 0 ? summary(trips) : 'Twoje zapisane podróże'}
        actions={filter}
      />
      {content}
    </Card>
  );
}
