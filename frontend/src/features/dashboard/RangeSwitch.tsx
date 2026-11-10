import { cn } from '@/lib/cn';
import { STATS_RANGES, type StatsRange } from '@/types/stats';

import { RANGE_LABELS } from './summary';

interface RangeSwitchProps {
  value: StatsRange;
  onChange: (range: StatsRange) => void;
}

/** Segmented control built on native radios, so arrow keys work. Scrolls sideways if narrow. */
export function RangeSwitch({ value, onChange }: RangeSwitchProps) {
  return (
    <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
      <fieldset className="flex w-max gap-1 rounded-xl border border-stone-200 bg-white p-1 shadow-xs">
        <legend className="sr-only">Time range</legend>
        {STATS_RANGES.map((range) => (
          <label
            key={range}
            className={cn(
              'cursor-pointer rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap transition',
              'text-stone-600 hover:text-stone-900',
              'has-checked:bg-emerald-600 has-checked:text-white',
              'has-focus-visible:ring-4 has-focus-visible:ring-emerald-100',
            )}
          >
            <input
              type="radio"
              name="stats-range"
              value={range}
              className="sr-only"
              checked={value === range}
              onChange={() => onChange(range)}
            />
            {RANGE_LABELS[range]}
          </label>
        ))}
      </fieldset>
    </div>
  );
}
