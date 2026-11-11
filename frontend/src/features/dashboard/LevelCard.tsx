import { cn } from '@/lib/cn';
import type { StatsLevel } from '@/types/stats';

import { LevelIcon, LockIcon } from './LevelIcon';
import { levelTheme } from './levelTheme';
import { nextLevelText } from './summary';

function Ladder({ level }: { level: StatsLevel }) {
  const theme = levelTheme(level.name);
  return (
    <ol aria-label="All levels" className="mt-5 grid grid-cols-5 gap-1">
      {level.ladder.map((step) => {
        const current = step.name === level.name;
        const stepTheme = levelTheme(step.name);
        return (
          <li
            key={step.name}
            className="flex flex-col items-center gap-1 text-center"
            aria-current={current ? 'step' : undefined}
          >
            <span
              className={cn(
                'relative flex size-9 items-center justify-center rounded-full',
                step.reached ? stepTheme.gradient : 'bg-white/30',
                step.reached ? stepTheme.text : 'text-stone-500',
                current && 'ring-2 ring-white ring-offset-2 ring-offset-transparent',
                !step.reached && 'opacity-70 grayscale',
              )}
            >
              <LevelIcon name={stepTheme.icon} className="size-5" />
              {!step.reached && (
                <span className="absolute -right-0.5 -bottom-0.5 rounded-full bg-stone-600 p-0.5 text-white">
                  <LockIcon className="size-2.5" />
                </span>
              )}
            </span>
            <span className={cn('text-[11px] leading-tight font-medium', theme.muted)}>
              {step.name}
              <span className="sr-only">
                {step.reached ? ', reached' : `, locked (${step.min_points} pts)`}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function LevelCard({ level }: { level: StatsLevel }) {
  const theme = levelTheme(level.name);
  const percent = Math.round(level.progress * 100);
  return (
    <section
      aria-labelledby="level-name"
      className={cn('rounded-2xl p-5 shadow-sm sm:p-6', theme.gradient, theme.text)}
    >
      <div className="flex items-center gap-4">
        <span
          className={cn(
            'flex size-14 shrink-0 items-center justify-center rounded-2xl shadow-inner',
            theme.badge,
          )}
        >
          <LevelIcon name={theme.icon} className="size-8" />
        </span>
        <div className="min-w-0">
          <p className={cn('text-xs font-medium tracking-wide uppercase', theme.muted)}>
            Your level
          </p>
          <h2 id="level-name" className="text-2xl font-bold">
            {level.name}
          </h2>
        </div>
        <p className="ml-auto text-right">
          <span className="block text-2xl font-bold tabular-nums">
            {level.points.toLocaleString('en-GB')}
          </span>
          <span className={cn('text-xs', theme.muted)}>eco-points</span>
        </p>
      </div>
      <progress
        aria-label={`Progress to ${level.next_level_name ?? 'the top level'}`}
        max={100}
        value={percent}
        className={cn(
          'mt-5 block h-3 w-full appearance-none overflow-hidden rounded-full bg-white/40',
          '[&::-webkit-progress-bar]:bg-white/40 [&::-webkit-progress-value]:rounded-full',
          theme.bar,
        )}
      />
      <p className="mt-2 text-sm font-medium">{nextLevelText(level)}</p>
      <Ladder level={level} />
      <p className={cn('mt-4 text-xs', theme.muted)}>
        10 points for every kg of CO₂ saved compared with going by petrol car.
      </p>
    </section>
  );
}
