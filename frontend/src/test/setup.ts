import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';

import { resetTripDb } from './handlers';
import { server } from './server';

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
beforeEach(() => resetTripDb());
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
