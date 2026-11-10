import { ComingSoon } from '@/components/ComingSoon';
import { PageHeader } from '@/components/PageHeader';

// TODO(compare): form (or free-text input parsed by the AI trip parser) + results table/cards
// for all transport modes, using /api/v1/compare once the emissions service exists.
export function ComparePage() {
  return (
    <>
      <PageHeader
        title="Porównaj środki transportu"
        description="Zobacz czas, koszt i emisję CO₂ tej samej trasy dla różnych środków transportu."
      />
      <ComingSoon
        title="Porównywarka jest w budowie"
        items={[
          'Porównanie auta, auta elektrycznego, pociągu, autokaru, samolotu i roweru',
          'Czas, koszt i kg CO₂ liczone deterministycznie po stronie serwera',
          'Wpisywanie trasy zwykłym tekstem (lokalny model AI przez Ollamę)',
          'Doradca AI, który wyjaśnia wynik i proponuje najlepszą opcję',
        ]}
      />
    </>
  );
}
