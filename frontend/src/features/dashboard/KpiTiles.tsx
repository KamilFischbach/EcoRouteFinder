import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';
import { formatCo2, formatDistance } from '@/lib/format';
import type { Stats } from '@/types/stats';

import { LevelIcon } from './LevelIcon';
import { levelTheme, type LevelTheme } from './levelTheme';
import { changeBadge, savedPhrase, type ChangeBadge } from './summary';

interface KpiTileProps {
  title: string;
  value: string;
  caption: ReactNode;
  change?: ChangeBadge | null;
  /** Gradient look of a level (the eco-points tile). */
  theme?: LevelTheme;
}

const ARROWS = { up: '↑', down: '↓', same: '→' } as const;

function Change({ change }: { change: ChangeBadge }) {
  const verdict = change.better === null ? '' : change.better ? 'better' : 'worse';
  return (
    <p
      className={cn(
        'mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        change.better === null && 'bg-stone-100 text-stone-600',
        change.better === true && 'bg-emerald-50 text-emerald-700',
        change.better === false && 'bg-red-50 text-red-700',
      )}
      title={change.description}
    >
      <span aria-hidden="true">{ARROWS[change.direction]}</span>
      <span className="sr-only">
        {verdict ? `${change.description}, ${verdict}` : change.description}
      </span>
      <span aria-hidden="true">
        {change.amount}
        {verdict && ` · ${verdict}`}
      </span>
    </p>
  );
}

function KpiTile({ title, value, caption, change, theme }: KpiTileProps) {
  const id = `kpi-${title.toLowerCase().replace(/[^a-z]+/g, '-')}`;
  return (
    <section
      aria-labelledby={id}
      className={cn(
        'relative overflow-hidden rounded-2xl p-4 shadow-sm sm:p-5',
        theme ? theme.gradient : 'border border-stone-200/80 bg-white',
      )}
    >
      {theme && (
        <LevelIcon
          name={theme.icon}
          className={cn('absolute -right-2 -bottom-2 size-20 opacity-25', theme.text)}
        />
      )}
      <h2
        id={id}
        className={cn('text-xs font-medium sm:text-sm', theme ? theme.muted : 'text-stone-500')}
      >
        {title}
      </h2>
      <p
        className={cn(
          'mt-1 text-xl font-semibold tabular-nums sm:text-2xl',
          theme ? theme.text : 'text-stone-900',
        )}
      >
        {value}
      </p>
      <p className={cn('mt-0.5 text-xs', theme ? theme.muted : 'text-stone-500')}>{caption}</p>
      {change && <Change change={change} />}
    </section>
  );
}

export function KpiTiles({ stats }: { stats: Stats }) {
  const { totals, previous_period: previous, range } = stats;
  const saved = totals.co2_saved_kg;
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      <KpiTile
        title="CO₂ footprint"
        value={formatCo2(totals.co2_kg)}
        caption="per person"
        change={changeBadge(previous?.co2_change_pct, range, true)}
      />
      <KpiTile
        title="CO₂ saved vs petrol car"
        value={formatCo2(Math.abs(saved))}
        caption={savedPhrase(saved)}
        change={changeBadge(previous?.saved_change_pct, range, false)}
      />
      <KpiTile
        title="Trips"
        value={totals.trips.toLocaleString('en-GB')}
        caption={`${formatDistance(totals.km_not_driven)} not driven by car`}
      />
      <KpiTile
        title="Eco-points"
        value={totals.eco_points.toLocaleString('en-GB')}
        caption={`Level: ${stats.level.name}`}
        theme={levelTheme(stats.level.name)}
      />
    </div>
  );
}
