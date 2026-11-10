import { ComingSoon } from '@/components/ComingSoon';
import { PageHeader } from '@/components/PageHeader';

// TODO(dashboard): Recharts charts fed by a /api/v1/stats endpoint.
export function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Twój ślad węglowy w czasie i to, ile CO₂ udało Ci się zaoszczędzić."
      />
      <ComingSoon
        title="Wykresy pojawią się wkrótce"
        items={[
          'Emisja CO₂ w czasie',
          'Zaoszczędzone kg CO₂ w porównaniu z jazdą autem',
          'Eko-punkty za wybór niskoemisyjnych środków transportu',
        ]}
      />
    </>
  );
}
