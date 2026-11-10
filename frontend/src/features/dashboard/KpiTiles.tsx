import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';
import { formatCo2, formatDistance } from '@/lib/format';
import type { Stats } from '@/types/stats';

import { changeBadge, savedPhrase, type ChangeBadge } from './summary';

interface KpiTileProps {
  title: string;
  value: string;
  caption: ReactNode;
  change?: ChangeBadge | null;
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

function KpiTile({ title, value, caption, change }: KpiTileProps) {
  const id = `kpi-${title.toLowerCase().replace(/[^a-z]+/g, '-')}`;
  return (
    <section
      aria-labelledby={id}
      className="rounded-2xl border border-stone-200/80 bg-white p-4 shadow-sm sm:p-5"
    >
      <h2 id={id} className="text-xs font-medium text-stone-500 sm:text-sm">
        {title}
      </h2>
      <p className="mt-1 text-xl font-semibold text-stone-900 tabular-nums sm:text-2xl">{value}</p>
      <p className="mt-0.5 text-xs text-stone-500">{caption}</p>
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
        caption={`${formatDistance(totals.km_not_driven)} not driven`}
      />
      <KpiTile
        title="Eco-points"
        value={totals.eco_points.toLocaleString('en-GB')}
        caption={`Level: ${stats.level.name}`}
      />
    </div>
  );
}
