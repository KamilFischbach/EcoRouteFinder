import { useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { Card } from '@/components/Card';
import type { AdvisorController } from '@/features/assistant/useTripAssistant';
import { useCreateTrip } from '@/features/trips/useTrips';
import { formatDistance } from '@/lib/format';
import { localIsoDate } from '@/lib/validators';
import type { Comparison, ComparisonOption, RouteSource } from '@/types/comparison';
import type { TransportMode } from '@/types/trip';

import { Co2Chart } from './Co2Chart';
import { EcoAdvisorCard } from './EcoAdvisorCard';
import { highlightsFor, sortOptions } from './highlights';
import { OptionCard, type SaveState } from './OptionCard';

const SOURCE_TEXT: Record<RouteSource, string> = {
  osrm: 'Road distance from OpenStreetMap (OSRM)',
  estimate: 'Map routing unavailable: straight-line distance × 1.25',
  user: 'Distance you entered',
};

function SourceBadge({ source }: { source: RouteSource }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs text-stone-500">
      {source === 'estimate' && (
        <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800">
          estimated
        </span>
      )}
      {SOURCE_TEXT[source]}
    </span>
  );
}

interface ComparisonResultsProps {
  comparison: Comparison;
  advisor: AdvisorController;
}

export function ComparisonResults({ comparison, advisor }: ComparisonResultsProps) {
  const { route, passengers } = comparison;
  const options = sortOptions(comparison.options);
  const createTrip = useCreateTrip();
  const [saved, setSaved] = useState<Set<TransportMode>>(new Set());
  const [failed, setFailed] = useState<{ mode: TransportMode; message: string } | null>(null);

  function saveState(mode: TransportMode): SaveState {
    if (saved.has(mode)) return 'saved';
    if (createTrip.isPending && createTrip.variables?.mode === mode) return 'saving';
    if (failed?.mode === mode) return 'error';
    return 'idle';
  }

  function save(option: ComparisonOption) {
    setFailed(null);
    createTrip.mutate(
      {
        origin: route.origin.name,
        destination: route.destination.name,
        distance_km: option.distance_km,
        passengers,
        mode: option.mode,
        note: null,
        travelled_on: localIsoDate(),
      },
      {
        onSuccess: () => setSaved((current) => new Set(current).add(option.mode)),
        onError: (error) => setFailed({ mode: option.mode, message: getErrorMessage(error) }),
      },
    );
  }

  return (
    <div className="space-y-6">
      {/* The advice is the main answer, so it comes first; it loads on its own. */}
      <EcoAdvisorCard comparison={comparison} advisor={advisor} />

      <Card className="px-5 py-5 sm:px-6">
        <h2 className="text-lg font-semibold text-stone-900">
          {route.origin.name} → {route.destination.name}
        </h2>
        <p className="mt-1 text-sm text-stone-600">
          {formatDistance(route.distance_km)} · {passengers}{' '}
          {passengers === 1 ? 'traveller' : 'travellers'} · values per person
        </p>
        <div className="mt-2">
          <SourceBadge source={route.source} />
        </div>
        <div className="mt-6">
          <Co2Chart options={options} recommended={comparison.advice?.recommended_mode ?? null} />
        </div>
      </Card>

      <ul aria-label="Transport options" className="grid gap-4 sm:grid-cols-2">
        {options.map((option) => (
          <OptionCard
            key={option.mode}
            option={option}
            passengers={passengers}
            highlights={highlightsFor(option.mode, comparison.highlights)}
            recommended={comparison.advice?.recommended_mode === option.mode}
            saveState={saveState(option.mode)}
            saveError={failed?.mode === option.mode ? failed.message : null}
            onSave={() => save(option)}
          />
        ))}
      </ul>
    </div>
  );
}
