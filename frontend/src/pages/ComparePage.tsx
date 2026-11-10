import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { getErrorMessage } from '@/api/errors';
import { Card, CardHeader } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageHeader } from '@/components/PageHeader';
import { Spinner } from '@/components/Spinner';
import { CompareForm } from '@/features/compare/CompareForm';
import { ComparisonResults } from '@/features/compare/ComparisonResults';
import { RecentComparisons } from '@/features/compare/RecentComparisons';
import { useCompareMutation, useComparisonQuery } from '@/features/compare/useCompare';

function parseId(raw: string | undefined): number | undefined {
  const id = Number(raw);
  return raw !== undefined && Number.isInteger(id) && id > 0 ? id : undefined;
}

function LoadingCard({ label }: { label: string }) {
  return (
    <Card className="flex justify-center py-20 text-emerald-600">
      <Spinner label={label} />
    </Card>
  );
}

export function ComparePage() {
  const params = useParams<{ id: string }>();
  const id = parseId(params.id);
  const navigate = useNavigate();
  const compare = useCompareMutation();
  const saved = useComparisonQuery(id);
  const { reset } = compare;

  // Opening another saved comparison clears a previous search error or result.
  useEffect(() => {
    reset();
  }, [id, reset]);

  let results;
  if (compare.isPending) {
    results = <LoadingCard label="Comparing transport options…" />;
  } else if (compare.isError) {
    results = (
      <Card>
        <ErrorState title="Couldn't compare this route" message={getErrorMessage(compare.error)} />
      </Card>
    );
  } else if (params.id !== undefined && (id === undefined || saved.isError)) {
    const notFound =
      id === undefined || (saved.error instanceof ApiError && saved.error.status === 404);
    results = (
      <Card>
        <ErrorState
          title={notFound ? 'Comparison not found' : "Couldn't load this comparison"}
          message={
            notFound ? 'It may have been deleted. Start a new one.' : getErrorMessage(saved.error)
          }
        />
      </Card>
    );
  } else if (saved.data) {
    results = <ComparisonResults key={saved.data.id} comparison={saved.data} />;
  } else if (id !== undefined) {
    results = <LoadingCard label="Loading comparison…" />;
  } else {
    results = (
      <Card>
        <EmptyState
          title="Where are you going?"
          description="Enter a route to compare time, cost and CO₂ per person for six ways to travel."
        />
      </Card>
    );
  }

  return (
    <>
      <PageHeader
        title="Compare transport modes"
        description="See the time, cost and CO₂ emissions of the same route for different ways to travel."
      />
      {/* Mobile: form, results, history. Desktop: form + history on the left, results on the right. */}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] lg:grid-rows-[auto_1fr]">
        <Card>
          <CardHeader title="Route" description="Where from, where to, and how many of you." />
          <div className="px-5 py-5 sm:px-6">
            <CompareForm
              isSubmitting={compare.isPending}
              onSubmit={(input) =>
                compare.mutate(input, {
                  onSuccess: (comparison) => navigate(`/compare/${comparison.id}`),
                })
              }
            />
          </div>
        </Card>
        <div aria-live="polite" className="lg:col-start-2 lg:row-span-2 lg:row-start-1">
          {results}
        </div>
        <div className="lg:col-start-1 lg:row-start-2">
          <RecentComparisons activeId={id} />
        </div>
      </div>
    </>
  );
}
