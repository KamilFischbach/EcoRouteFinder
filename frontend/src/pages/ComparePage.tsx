import { ComingSoon } from '@/components/ComingSoon';
import { PageHeader } from '@/components/PageHeader';

// TODO(compare): form (or free-text input parsed by the AI trip parser) + results table/cards
// for all transport modes, using /api/v1/compare once the emissions service exists.
export function ComparePage() {
  return (
    <>
      <PageHeader
        title="Compare transport modes"
        description="See the time, cost and CO₂ emissions of the same route for different ways to travel."
      />
      <ComingSoon
        title="The comparison tool is under construction"
        items={[
          'Compare petrol car, electric car, train, coach, plane and bike',
          'Time, cost and kg CO₂ calculated deterministically on the server',
          'Describe a trip in plain text (local AI model via Ollama)',
          'An AI advisor that explains the results and suggests the best option',
        ]}
      />
    </>
  );
}
