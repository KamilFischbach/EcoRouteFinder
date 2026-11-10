import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { Spinner } from '@/components/Spinner';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { TripsPage } from '@/pages/TripsPage';

// The compare and dashboard pages pull in Recharts; load them only when visited.
const ComparePage = lazy(() =>
  import('@/pages/ComparePage').then((module) => ({ default: module.ComparePage })),
);
const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage })),
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
        {['compare', 'compare/:id'].map((path) => (
          <Route
            key={path}
            path={path}
            element={
              <Suspense fallback={<PageFallback />}>
                <ComparePage />
              </Suspense>
            }
          />
        ))}
        <Route
          path="dashboard"
          element={
            <Suspense fallback={<PageFallback />}>
              <DashboardPage />
            </Suspense>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
