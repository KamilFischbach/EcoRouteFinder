import { ComingSoon } from '@/components/ComingSoon';
import { PageHeader } from '@/components/PageHeader';

// TODO(dashboard): Recharts charts fed by a /api/v1/stats endpoint.
export function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Your carbon footprint over time and how much CO₂ you have saved."
      />
      <ComingSoon
        title="Charts are coming soon"
        items={[
          'CO₂ emissions over time',
          'kg of CO₂ saved compared to driving',
          'Eco-points for choosing low-emission transport',
        ]}
      />
    </>
  );
}
