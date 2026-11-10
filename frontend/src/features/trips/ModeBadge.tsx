import { cn } from '@/lib/cn';
import { MODE_LABELS, type TransportMode } from '@/types/trip';

const MODE_STYLES: Record<TransportMode, string> = {
  car_petrol: 'bg-orange-50 text-orange-700 ring-orange-200',
  car_ev: 'bg-sky-50 text-sky-700 ring-sky-200',
  train: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  coach: 'bg-teal-50 text-teal-700 ring-teal-200',
  plane: 'bg-rose-50 text-rose-700 ring-rose-200',
  bike: 'bg-lime-50 text-lime-800 ring-lime-200',
};

export function ModeBadge({ mode }: { mode: TransportMode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        MODE_STYLES[mode],
      )}
    >
      {MODE_LABELS[mode]}
    </span>
  );
}
