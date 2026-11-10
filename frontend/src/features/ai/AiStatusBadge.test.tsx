import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';

import { AiStatusBadge } from './AiStatusBadge';

function health(body: object, status = 200) {
  server.use(http.get(`${API_URL}/health`, () => HttpResponse.json(body, { status })));
}

describe('AiStatusBadge', () => {
  it('shows the model when AI is online', async () => {
    renderWithProviders(<AiStatusBadge />);

    expect(await screen.findByRole('status')).toHaveTextContent('AI online · qwen3:8b');
  });

  it('shows rule-based mode when Ollama is offline', async () => {
    health({ status: 'ok', ai_available: false, ai_model: 'qwen3:8b' });
    renderWithProviders(<AiStatusBadge />);

    expect(await screen.findByRole('status')).toHaveTextContent('AI offline (rule-based)');
  });

  it('shows rule-based mode when AI is disabled', async () => {
    health({ status: 'ok', ai_available: false, ai_model: null });
    renderWithProviders(<AiStatusBadge />);

    expect(await screen.findByRole('status')).toHaveTextContent('AI offline (rule-based)');
  });

  it('shows that the API is unreachable', async () => {
    health({ error: { code: 'INTERNAL_ERROR', message: 'x', details: null } }, 500);
    renderWithProviders(<AiStatusBadge />);

    expect(await screen.findByRole('status')).toHaveTextContent('API offline');
  });
});
