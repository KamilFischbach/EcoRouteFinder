import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { Spinner } from '@/components/Spinner';
import { DashboardPage } from '@/pages/DashboardPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { TripsPage } from '@/pages/TripsPage';

// The compare page pulls in Recharts; load it only when visited.
const ComparePage = lazy(() =>
  import('@/pages/ComparePage').then((module) => ({ default: module.ComparePage })),
);

function PageFallback() {
  return (
    <div className="flex justify-center py-20 text-emerald-600">
      <Spinner label="Loading…" />
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<TripsPage />} />
        <Route
          path="compare"
          element={
            <Suspense fallback={<PageFallback />}>
              <ComparePage />
            </Suspense>
          }
        />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
