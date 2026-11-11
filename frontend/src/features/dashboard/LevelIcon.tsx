import { cn } from '@/lib/cn';

import type { LevelIconName } from './levelTheme';

const PATHS: Record<LevelIconName, string[]> = {
  // A seed with one small leaf.
  seedling: ['M12 21v-5', 'M12 16c-2.5 0-4-1.6-4-4 2.5 0 4 1.6 4 4Z', 'M8 21h8'],
  // Two leaves.
  sprout: [
    'M12 21v-9',
    'M12 13c-3.5 0-5.5-2.2-5.5-5.5 3.5 0 5.5 2.2 5.5 5.5Z',
    'M12 11c0-3.3 2-5.5 5.5-5.5 0 3.3-2 5.5-5.5 5.5Z',
    'M7 21h10',
  ],
  // A young tree.
  sapling: [
    'M12 21v-6',
    'M12 3c3.3 0 6 2.9 6 6.5S15.3 15 12 15s-6-2.1-6-5.5S8.7 3 12 3Z',
    'M7 21h10',
  ],
  // A tall pine.
  tree: ['M12 2 6 10h3l-4 6h14l-4-6h3L12 2Z', 'M12 16v6'],
  // Three pines.
  forest: [
    'M8 4 4 10h2.5L3 15h10l-3.5-5H12L8 4Z',
    'M16 2l-4 6h2.5L11 13h10l-3.5-5H20l-4-6Z',
    'M8 15v6',
    'M16 13v8',
  ],
};

interface LevelIconProps {
  name: LevelIconName;
  className?: string;
}

/** Decorative; the level name is always shown as text next to it. */
export function LevelIcon({ name, className }: LevelIconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={cn('size-6', className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {PATHS[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

export function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={cn('size-3', className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}
