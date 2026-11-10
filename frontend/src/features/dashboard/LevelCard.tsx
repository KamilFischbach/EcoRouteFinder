import { Card } from '@/components/Card';
import { cn } from '@/lib/cn';
import type { StatsLevel } from '@/types/stats';

import { nextLevelText } from './summary';

export function LevelCard({ level }: { level: StatsLevel }) {
  const percent = Math.round(level.progress * 100);
  return (
    <Card className="p-5 sm:p-6">
      <p className="text-sm text-stone-500">Your level</p>
      <h2 className="mt-1 text-xl font-semibold text-emerald-700">{level.name}</h2>
      <progress
        aria-label={`Progress to ${level.next_level_name ?? 'the top level'}`}
        max={100}
        value={percent}
        className={cn(
          'mt-4 block h-2.5 w-full appearance-none overflow-hidden rounded-full bg-stone-100',
          '[&::-webkit-progress-bar]:bg-stone-100 [&::-webkit-progress-value]:rounded-full',
          '[&::-webkit-progress-value]:bg-emerald-500 [&::-moz-progress-bar]:bg-emerald-500',
        )}
      />
      <p className="mt-2 text-sm text-stone-600">
        <span className="font-medium text-stone-900 tabular-nums">
          {level.points.toLocaleString('en-GB')} pts
        </span>
        {' · '}
        {nextLevelText(level)}
      </p>
      <p className="mt-3 text-xs text-stone-500">
        10 points for every kg of CO₂ saved compared with going by petrol car.
      </p>
    </Card>
  );
}
