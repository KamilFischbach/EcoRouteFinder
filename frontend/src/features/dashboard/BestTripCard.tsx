import { Card } from '@/components/Card';
import { ModeBadge } from '@/features/trips/ModeBadge';
import { formatCo2, formatDay, formatDistance } from '@/lib/format';
import type { StatsBestTrip } from '@/types/stats';

export function BestTripCard({ trip }: { trip: StatsBestTrip | null }) {
  return (
    <Card className="p-5 sm:p-6">
      <h2 className="text-sm text-stone-500">Best trip</h2>
      {trip ? (
        <>
          <p className="mt-1 text-lg font-semibold text-stone-900">
            {trip.origin} → {trip.destination}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-stone-500">
            <ModeBadge mode={trip.mode} />
            <span>{formatDay(trip.travelled_on)}</span>
            <span>
              · {formatDistance(trip.distance_km)} · {trip.passengers}{' '}
              {trip.passengers === 1 ? 'person' : 'people'}
            </span>
          </div>
          <p className="mt-3 text-sm text-stone-700">
            Saved{' '}
            <span className="font-semibold text-emerald-700">{formatCo2(trip.co2_saved_kg)}</span>{' '}
            of CO₂ per person compared with going by petrol car.
          </p>
        </>
      ) : (
        <p className="mt-1 text-sm text-stone-600">
          No trip in this period saved CO₂ compared with going by petrol car.
        </p>
      )}
    </Card>
  );
}
