import { cn } from './cn';

export function inputClass(invalid = false): string {
  return cn(
    'block w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm text-stone-900 shadow-xs',
    'placeholder:text-stone-400 transition focus:outline-none focus:ring-4',
    invalid
      ? 'border-red-300 focus:border-red-400 focus:ring-red-100'
      : 'border-stone-200 focus:border-emerald-500 focus:ring-emerald-100',
  );
}
