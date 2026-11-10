import type { ComponentProps, ReactNode } from 'react';

import { cn } from '@/lib/cn';

export function Card({ className, ...props }: ComponentProps<'section'>) {
  return (
    <section
      className={cn('rounded-2xl border border-stone-200/80 bg-white shadow-sm', className)}
      {...props}
    />
  );
}

interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function CardHeader({ title, description, actions }: CardHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-stone-100 px-5 py-4 sm:px-6">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-stone-900">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-stone-500">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
