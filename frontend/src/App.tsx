import { Route, Routes } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { ComparePage } from '@/pages/ComparePage';
import { DashboardPage } from '@/pages/DashboardPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { TripsPage } from '@/pages/TripsPage';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<TripsPage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
