import { Link, useSearchParams } from 'react-router-dom';

import { getErrorMessage } from '@/api/errors';
import { Card, CardHeader } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageHeader } from '@/components/PageHeader';
import { BestTripCard } from '@/features/dashboard/BestTripCard';
import { KpiTiles } from '@/features/dashboard/KpiTiles';
import { LevelCard } from '@/features/dashboard/LevelCard';
import { ModeChart } from '@/features/dashboard/ModeChart';
import { RangeSwitch } from '@/features/dashboard/RangeSwitch';
import { RANGE_LABELS, parseRange, summarySentence } from '@/features/dashboard/summary';
import { TimelineChart } from '@/features/dashboard/TimelineChart';
import { useStatsQuery } from '@/features/dashboard/useStats';
import type { Stats, StatsRange } from '@/types/stats';

function DashboardSkeleton() {
  return (
    <div aria-busy="true">
      <p role="status" className="sr-only">
        Loading your dashboard…
      </p>
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((tile) => (
          <div key={tile} className="h-28 animate-pulse rounded-2xl bg-stone-200/70" />
        ))}
      </div>
      <div className="mt-6 h-80 animate-pulse rounded-2xl bg-stone-200/50" />
    </div>
  );
}

function DashboardEmpty({ range }: { range: StatsRange }) {
  return (
    <Card>
      <EmptyState
        title={range === 'all' ? 'No trips yet' : `No trips in the last ${RANGE_LABELS[range]}`}
        description="Save a trip from the comparison page to see your footprint here."
        action={
          <Link
            to="/compare"
            className="inline-flex h-10 items-center rounded-xl bg-emerald-600 px-4 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
          >
            Compare a route
          </Link>
        }
      />
    </Card>
  );
}

function DashboardContent({ stats }: { stats: Stats }) {
  const summary = summarySentence(stats);
  return (
    <div className="space-y-6">
      {summary && (
        <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{summary}</p>
      )}
      <KpiTiles stats={stats} />
      <Card>
        <CardHeader
          title="CO₂ over time"
          description={`Per ${stats.granularity}, kg per person. Bars: footprint. Line: saved vs petrol car.`}
        />
        <div className="px-3 py-4 sm:px-6">
          <TimelineChart timeline={stats.timeline} granularity={stats.granularity} />
        </div>
      </Card>
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="CO₂ by transport mode" description="kg per person" />
          <div className="px-3 py-4 sm:px-6">
            <ModeChart byMode={stats.by_mode} />
          </div>
        </Card>
        <div className="space-y-6">
          <LevelCard level={stats.level} />
          <BestTripCard trip={stats.best_trip} />
        </div>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = parseRange(searchParams.get('range'));
  const stats = useStatsQuery(range);

  function renderBody() {
    if (stats.isPending) return <DashboardSkeleton />;
    if (stats.isError) {
      return (
        <Card>
          <ErrorState
            title="Could not load your dashboard"
            message={getErrorMessage(stats.error)}
            onRetry={() => void stats.refetch()}
          />
        </Card>
      );
    }
    if (stats.data.totals.trips === 0) return <DashboardEmpty range={range} />;
    return <DashboardContent stats={stats.data} />;
  }

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Your carbon footprint over time and how much CO₂ you saved by not taking a petrol car. All values are per person."
        actions={
          <RangeSwitch value={range} onChange={(next) => setSearchParams({ range: next })} />
        }
      />
      {renderBody()}
    </>
  );
}
