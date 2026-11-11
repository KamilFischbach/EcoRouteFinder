// Look of each eco-level: a gradient that deepens as the level grows. Names come from the server
// (backend/app/services/eco_points.py LEVELS); an unknown name falls back to the first theme.

export type LevelIconName = 'seedling' | 'sprout' | 'sapling' | 'tree' | 'forest';

export interface LevelTheme {
  icon: LevelIconName;
  /** Card background. */
  gradient: string;
  /** Main text on the gradient. */
  text: string;
  /** Secondary text on the gradient. */
  muted: string;
  /** Circle behind the icon. */
  badge: string;
  /** Progress bar value. */
  bar: string;
}

const THEMES: Record<string, LevelTheme> = {
  Seedling: {
    icon: 'seedling',
    gradient: 'bg-linear-to-br from-lime-50 via-lime-100 to-lime-200',
    text: 'text-lime-950',
    muted: 'text-lime-800',
    badge: 'bg-white/70 text-lime-700',
    bar: '[&::-webkit-progress-value]:bg-lime-600 [&::-moz-progress-bar]:bg-lime-600',
  },
  Sprout: {
    icon: 'sprout',
    gradient: 'bg-linear-to-br from-lime-100 via-emerald-100 to-emerald-200',
    text: 'text-emerald-950',
    muted: 'text-emerald-800',
    badge: 'bg-white/70 text-emerald-700',
    bar: '[&::-webkit-progress-value]:bg-emerald-600 [&::-moz-progress-bar]:bg-emerald-600',
  },
  Sapling: {
    icon: 'sapling',
    gradient: 'bg-linear-to-br from-emerald-200 via-emerald-300 to-teal-400',
    text: 'text-emerald-950',
    muted: 'text-emerald-900',
    badge: 'bg-white/60 text-emerald-800',
    bar: '[&::-webkit-progress-value]:bg-emerald-800 [&::-moz-progress-bar]:bg-emerald-800',
  },
  Tree: {
    icon: 'tree',
    gradient: 'bg-linear-to-br from-emerald-500 via-emerald-600 to-teal-700',
    text: 'text-white',
    muted: 'text-emerald-50',
    badge: 'bg-white/20 text-white',
    bar: '[&::-webkit-progress-value]:bg-white [&::-moz-progress-bar]:bg-white',
  },
  Forest: {
    icon: 'forest',
    gradient: 'bg-linear-to-br from-emerald-800 via-emerald-900 to-teal-950',
    text: 'text-white',
    muted: 'text-emerald-100',
    badge: 'bg-white/15 text-lime-200',
    bar: '[&::-webkit-progress-value]:bg-lime-300 [&::-moz-progress-bar]:bg-lime-300',
  },
};

export function levelTheme(name: string): LevelTheme {
  return THEMES[name] ?? THEMES.Seedling!;
}
