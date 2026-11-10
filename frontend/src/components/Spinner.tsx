import { cn } from '@/lib/cn';

interface SpinnerProps {
  size?: 'sm' | 'md';
  /** When set, the spinner is announced to screen readers and the label is shown. */
  label?: string;
}

export function Spinner({ size = 'md', label }: SpinnerProps) {
  return (
    <span role={label ? 'status' : undefined} className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className={cn(
          'animate-spin rounded-full border-2 border-current border-t-transparent',
          size === 'sm' ? 'size-4' : 'size-6',
        )}
      />
      {label && <span className="text-sm">{label}</span>}
    </span>
  );
}
