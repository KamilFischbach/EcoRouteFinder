import { Link } from 'react-router-dom';

import { AiIcon } from '@/components/AiIcon';
import { Button } from '@/components/Button';
import { cn } from '@/lib/cn';
import { formatCo2, formatCost, formatDistance, formatDuration } from '@/lib/format';
import type { ComparisonOption } from '@/types/comparison';
import { MODE_LABELS } from '@/types/trip';

import { savingsLabel, type Highlight } from './highlights';

export type SaveState = 'idle' | 'saving' | 'saved' | 'error';

interface OptionCardProps {
  option: ComparisonOption;
  highlights: Highlight[];
  saveState: SaveState;
  saveError?: string | null;
  /** EcoAdvisor recommended this option. */
  recommended?: boolean;
  onSave: () => void;
}

const HIGHLIGHT_STYLES: Record<Highlight, string> = {
  Greenest: 'bg-emerald-600 text-white',
  Fastest: 'bg-sky-100 text-sky-800',
  Cheapest: 'bg-amber-100 text-amber-800',
};

export function OptionCard({
  option,
  highlights,
  saveState,
  saveError,
  recommended = false,
  onSave,
}: OptionCardProps) {
  const label = MODE_LABELS[option.mode];
  const saved = option.co2_saved_vs_car_kg;

  return (
    <li
      aria-label={label}
      className={cn(
        'flex flex-col rounded-2xl border bg-white p-5 shadow-sm',
        highlights.includes('Greenest') ? 'border-emerald-300' : 'border-stone-200/80',
        recommended && 'border-violet-300 ring-2 ring-violet-200',
        !option.practical && 'bg-stone-50 shadow-none',
      )}
    >
      {recommended && (
        <span className="mb-2 inline-flex w-fit items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800">
          <AiIcon className="size-3" />
          EcoAdvisor pick
        </span>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <h3 className={cn('font-semibold', option.practical ? 'text-stone-900' : 'text-stone-500')}>
          {label}
        </h3>
        {highlights.map((highlight) => (
          <span
            key={highlight}
            className={cn(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              HIGHLIGHT_STYLES[highlight],
            )}
          >
            {highlight}
          </span>
        ))}
        {!option.practical && (
          <span className="rounded-full bg-stone-200 px-2 py-0.5 text-xs font-medium text-stone-600">
            Not practical
          </span>
        )}
      </div>

      <p
        className={cn(
          'mt-3 text-2xl font-semibold tabular-nums',
          option.practical ? 'text-stone-900' : 'text-stone-400',
        )}
      >
        {formatCo2(option.co2_kg)}{' '}
        <span className="text-sm font-normal text-stone-500">CO₂ per person</span>
      </p>
      <p
        className={cn(
          'mt-1 text-sm',
          !option.practical ? 'text-stone-400' : saved > 0 ? 'text-emerald-700' : 'text-stone-500',
        )}
      >
        {savingsLabel(saved)}
      </p>

      {option.note && <p className="mt-2 text-sm text-stone-500">{option.note}</p>}

      <dl
        className={cn(
          'mt-4 grid grid-cols-3 gap-2 border-t border-stone-100 pt-4 text-sm',
          !option.practical && 'text-stone-400',
        )}
      >
        <div>
          <dt className="text-xs text-stone-500">Time</dt>
          <dd className="font-medium tabular-nums">{formatDuration(option.duration_min)}</dd>
        </div>
        <div>
          <dt className="text-xs text-stone-500">Cost</dt>
          <dd className="font-medium tabular-nums">~{formatCost(option.cost_pln)}</dd>
        </div>
        <div>
          <dt className="text-xs text-stone-500">Distance</dt>
          <dd className="font-medium tabular-nums">{formatDistance(option.distance_km)}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {saveState === 'saved' ? (
          <p role="status" className="text-sm font-medium text-emerald-700">
            Saved to your trips ·{' '}
            <Link to="/" className="underline hover:text-emerald-800">
              View
            </Link>
          </p>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            isLoading={saveState === 'saving'}
            aria-label={`Save trip by ${label}`}
            onClick={onSave}
          >
            Save trip
          </Button>
        )}
        {saveState === 'error' && saveError && (
          <p role="alert" className="text-sm text-red-600">
            {saveError}
          </p>
        )}
      </div>
    </li>
  );
}
