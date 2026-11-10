import { getErrorMessage } from '@/api/errors';
import { Card, CardHeader } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageHeader } from '@/components/PageHeader';
import { Spinner } from '@/components/Spinner';
import { CompareForm } from '@/features/compare/CompareForm';
import { ComparisonResults } from '@/features/compare/ComparisonResults';
import { useCompareMutation } from '@/features/compare/useCompare';

export function ComparePage() {
  const compare = useCompareMutation();

  let results;
  if (compare.isPending) {
    results = (
      <Card className="flex justify-center py-20 text-emerald-600">
        <Spinner label="Comparing transport options…" />
      </Card>
    );
  } else if (compare.isError) {
    results = (
      <Card>
        <ErrorState title="Couldn't compare this route" message={getErrorMessage(compare.error)} />
      </Card>
    );
  } else if (compare.data) {
    results = (
      <ComparisonResults key={JSON.stringify(compare.variables)} comparison={compare.data} />
    );
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
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        <Card className="lg:sticky lg:top-24">
          <CardHeader title="Route" description="Where from, where to, and how many of you." />
          <div className="px-5 py-5 sm:px-6">
            <CompareForm
              isSubmitting={compare.isPending}
              onSubmit={(input) => compare.mutate(input)}
            />
          </div>
        </Card>
        <div aria-live="polite">{results}</div>
      </div>
    </>
  );
}
