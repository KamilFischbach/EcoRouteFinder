import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { getErrorMessage } from '@/api/errors';
import { Button } from '@/components/Button';
import { Card, CardHeader } from '@/components/Card';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { ErrorState } from '@/components/ErrorState';
import { Spinner } from '@/components/Spinner';
import { ModeBadge } from '@/features/trips/ModeBadge';
import { cn } from '@/lib/cn';
import { formatCo2, formatRelativeTime } from '@/lib/format';
import type { ComparisonSummary } from '@/types/comparison';
import { MODE_LABELS } from '@/types/trip';

import { useComparisonsQuery, useDeleteComparison } from './useCompare';

function savedKg(row: ComparisonSummary): number | null {
  return row.greenest_co2_kg === null ? null : row.petrol_car_co2_kg - row.greenest_co2_kg;
}

function RecentRow({
  row,
  active,
  onDelete,
}: {
  row: ComparisonSummary;
  active: boolean;
  onDelete: () => void;
}) {
  const route = `${row.origin} → ${row.destination}`;
  const saved = savedKg(row);
  return (
    <li className={cn('flex items-start gap-2 px-5 py-3 sm:px-6', active && 'bg-emerald-50/70')}>
      <Link
        to={`/compare/${row.id}`}
        aria-current={active ? 'page' : undefined}
        className="min-w-0 flex-1 rounded-lg focus-visible:outline-2 focus-visible:outline-emerald-600"
      >
        <span className="block truncate text-sm font-medium text-stone-900">{route}</span>
        <span className="mt-0.5 block text-xs text-stone-500">
          {formatRelativeTime(row.created_at)} · {row.passengers}{' '}
          {row.passengers === 1 ? 'traveller' : 'travellers'}
        </span>
        <span className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-stone-600">
          {row.greenest_mode ? (
            <>
              <ModeBadge mode={row.greenest_mode} />
              {saved !== null && saved > 0 && (
                <span>saves {formatCo2(saved)} CO₂ vs petrol car</span>
              )}
            </>
          ) : (
            <span>No practical option</span>
          )}
          {row.recommended_mode && (
            <span className="rounded-full bg-sky-50 px-2 py-0.5 font-medium text-sky-800 ring-1 ring-sky-200 ring-inset">
              Advisor: {MODE_LABELS[row.recommended_mode]}
            </span>
          )}
        </span>
      </Link>
      <Button
        variant="ghost"
        size="sm"
        className="text-stone-400 hover:bg-red-50 hover:text-red-600"
        aria-label={`Delete comparison ${route}`}
        onClick={onDelete}
      >
        <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="size-4">
          <path d="M8.5 2a1 1 0 0 0-1 1v.5H4.75a.75.75 0 0 0 0 1.5h.3l.7 10.1A2 2 0 0 0 7.74 17h4.52a2 2 0 0 0 2-1.9L14.95 5h.3a.75.75 0 0 0 0-1.5H12.5V3a1 1 0 0 0-1-1h-3Z" />
        </svg>
      </Button>
    </li>
  );
}

export function RecentComparisons({ activeId }: { activeId?: number }) {
  const { data, isPending, isError, error, refetch } = useComparisonsQuery();
  const deleteComparison = useDeleteComparison();
  const [toDelete, setToDelete] = useState<ComparisonSummary | null>(null);
  const navigate = useNavigate();

  function confirmDelete() {
    if (!toDelete) return;
    const deletedId = toDelete.id;
    deleteComparison.mutate(deletedId, {
      onSuccess: () => {
        setToDelete(null);
        if (deletedId === activeId) navigate('/compare');
      },
    });
  }

  let content;
  if (isPending) {
    content = (
      <div className="flex justify-center py-8 text-emerald-600">
        <Spinner label="Loading history…" />
      </div>
    );
  } else if (isError) {
    content = <ErrorState message={getErrorMessage(error)} onRetry={() => void refetch()} />;
  } else if (data.length === 0) {
    content = (
      <p className="px-5 py-8 text-center text-sm text-stone-500 sm:px-6">
        No comparisons yet. Your searches will show up here.
      </p>
    );
  } else {
    content = (
      <ul aria-label="Recent comparisons" className="divide-y divide-stone-100">
        {data.map((row) => (
          <RecentRow
            key={row.id}
            row={row}
            active={row.id === activeId}
            onDelete={() => setToDelete(row)}
          />
        ))}
      </ul>
    );
  }

  return (
    <Card>
      <CardHeader title="Recent comparisons" />
      {content}
      <ConfirmDialog
        open={toDelete !== null}
        title="Delete this comparison?"
        description={
          toDelete
            ? `The comparison ${toDelete.origin} → ${toDelete.destination} will be removed from your history.`
            : ''
        }
        confirmLabel="Delete"
        isPending={deleteComparison.isPending}
        error={deleteComparison.isError ? getErrorMessage(deleteComparison.error) : null}
        onConfirm={confirmDelete}
        onCancel={() => {
          setToDelete(null);
          deleteComparison.reset();
        }}
      />
    </Card>
  );
}
