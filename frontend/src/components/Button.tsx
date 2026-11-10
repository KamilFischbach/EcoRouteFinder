import type { ComponentProps } from 'react';

import { cn } from '@/lib/cn';

import { Spinner } from './Spinner';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 focus-visible:outline-emerald-600',
  secondary:
    'bg-white text-stone-700 ring-1 ring-inset ring-stone-200 hover:bg-stone-50 focus-visible:outline-emerald-600',
  ghost: 'text-stone-600 hover:bg-stone-100 hover:text-stone-900 focus-visible:outline-emerald-600',
  danger: 'bg-red-600 text-white shadow-sm hover:bg-red-700 focus-visible:outline-red-600',
};

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
};

export interface ButtonProps extends ComponentProps<'button'> {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  type = 'button',
  className,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={cn(
        'inline-flex shrink-0 items-center justify-center gap-2 rounded-xl font-medium transition-colors',
        'focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    >
      {isLoading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
