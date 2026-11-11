import { Button } from '@/components/Button';
import { cn } from '@/lib/cn';
import { formatCo2, formatDay, formatDistance } from '@/lib/format';
import { localIsoDate } from '@/lib/validators';
import type { Trip } from '@/types/trip';

import { ModeBadge } from './ModeBadge';

interface TripTableProps {
  trips: Trip[];
  editingId?: number | null;
  onEdit: (trip: Trip) => void;
  onDelete: (trip: Trip) => void;
}

const TH = 'px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-stone-500';

export function TripTable({ trips, editingId, onEdit, onDelete }: TripTableProps) {
  const today = localIsoDate();
  return (
    // About 7 rows tall; longer lists scroll inside the card and the header stays visible.
    <div
      className="max-h-[32rem] overflow-auto"
      tabIndex={0}
      role="region"
      aria-label="Saved trips, scrollable"
    >
      <table className="w-full text-sm">
        <caption className="sr-only">Saved trips</caption>
        <thead className="sticky top-0 z-10 bg-stone-50">
          <tr>
            <th scope="col" className={cn(TH, 'sm:pl-6')}>
              Route
            </th>
            <th scope="col" className={cn(TH, 'hidden md:table-cell')}>
              Distance
            </th>
            <th scope="col" className={cn(TH, 'hidden md:table-cell')}>
              Passengers
            </th>
            <th scope="col" className={cn(TH, 'hidden sm:table-cell')}>
              Transport
            </th>
            <th scope="col" className={cn(TH, 'hidden sm:table-cell')}>
              CO₂ / person
            </th>
            <th scope="col" className={cn(TH, 'text-right sm:pr-6')}>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {trips.map((trip) => {
            const route = `${trip.origin} → ${trip.destination}`;
            const planned = trip.travelled_on > today;
            return (
              <tr
                key={trip.id}
                className={cn(
                  'transition-colors hover:bg-stone-50/60',
                  editingId === trip.id &&
                    'bg-emerald-50 shadow-[inset_4px_0_0_var(--color-emerald-500)] hover:bg-emerald-50',
                )}
              >
                <td className="px-4 py-3.5 sm:pl-6">
                  <div className="font-medium whitespace-nowrap text-stone-900">{route}</div>
                  <div className="mt-0.5 text-xs text-stone-500">
                    {formatDay(trip.travelled_on)}
                    {planned && (
                      <span className="ml-1.5 rounded-full bg-sky-50 px-1.5 py-px text-[11px] font-medium text-sky-700 ring-1 ring-sky-200 ring-inset">
                        Planned
                      </span>
                    )}
                    <span className="md:hidden">
                      {' · '}
                      {formatDistance(trip.distance_km)} · {trip.passengers}{' '}
                      {trip.passengers === 1 ? 'passenger' : 'passengers'}
                    </span>
                  </div>
                  {trip.note && (
                    <div className="mt-1 line-clamp-1 text-xs text-stone-500 italic">
                      {trip.note}
                    </div>
                  )}
                  <div className="mt-2 flex items-center gap-2 sm:hidden">
                    <ModeBadge mode={trip.mode} />
                    <span className="text-xs text-stone-600 tabular-nums">
                      {formatCo2(trip.co2_kg)} CO₂
                    </span>
                  </div>
                </td>
                <td className="hidden px-4 py-3.5 whitespace-nowrap text-stone-700 tabular-nums md:table-cell">
                  {formatDistance(trip.distance_km)}
                </td>
                <td className="hidden px-4 py-3.5 text-stone-700 tabular-nums md:table-cell">
                  {trip.passengers}
                </td>
                <td className="hidden px-4 py-3.5 sm:table-cell">
                  <ModeBadge mode={trip.mode} />
                </td>
                <td
                  className={cn(
                    'hidden px-4 py-3.5 whitespace-nowrap tabular-nums sm:table-cell',
                    trip.co2_kg === null ? 'text-stone-400' : 'text-stone-700',
                  )}
                  title={
                    trip.co2_kg === null ? 'Edit and save this trip to calculate CO₂' : undefined
                  }
                >
                  {formatCo2(trip.co2_kg)}
                </td>
                <td className="px-4 py-3.5 text-right whitespace-nowrap sm:pr-6">
                  <div className="inline-flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Edit trip ${route}`}
                      onClick={() => onEdit(trip)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:bg-red-50 hover:text-red-700"
                      aria-label={`Delete trip ${route}`}
                      onClick={() => onDelete(trip)}
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
