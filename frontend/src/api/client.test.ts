import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { server } from '@/test/server';

import { API_URL, ApiError, apiFetch } from './client';
import { getErrorMessage } from './errors';

describe('apiFetch timeout', () => {
  it('fails with TIMEOUT when the server is slower than timeoutMs', async () => {
    server.use(
      http.get(`${API_URL}/slow`, async () => {
        await delay(200);
        return HttpResponse.json({ ok: true });
      }),
    );

    const error: unknown = await apiFetch('/slow', { timeoutMs: 20 }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe('TIMEOUT');
    expect(getErrorMessage(error)).toBe('This is taking too long. Please try again.');
  });

  it('returns the body when the server answers in time', async () => {
    server.use(http.get(`${API_URL}/fast`, () => HttpResponse.json({ ok: true })));

    await expect(apiFetch('/fast', { timeoutMs: 1000 })).resolves.toEqual({ ok: true });
  });
});
