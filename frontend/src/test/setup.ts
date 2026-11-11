import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';

import { resetComparisonDb, resetMcp, resetTripDb } from './handlers';
import { server } from './server';

// jsdom has no ResizeObserver; Recharts' ResponsiveContainer needs one to mount.
class ResizeObserverStub {
  observe() {
    // no-op: tests don't need layout
  }
  unobserve() {
    // no-op
  }
  disconnect() {
    // no-op
  }
}
globalThis.ResizeObserver ??= ResizeObserverStub;

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
beforeEach(() => {
  resetTripDb();
  resetComparisonDb();
});
afterEach(() => {
  cleanup();
  resetMcp();
  window.localStorage.clear(); // e.g. the remembered trip assistant mode
  server.resetHandlers();
});
afterAll(() => server.close());
