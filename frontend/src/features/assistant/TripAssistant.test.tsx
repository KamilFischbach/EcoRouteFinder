import { screen, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import { ComparePage } from '@/pages/ComparePage';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';
import type { TripDraft } from '@/types/tripDraft';

function renderPage(route = '/compare') {
  return renderWithProviders(
    <Routes>
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/compare/:id" element={<ComparePage />} />
    </Routes>,
    { route },
  );
}

const assistant = () => screen.getByRole('region', { name: 'Trip assistant' });
const step = (name: RegExp) => within(assistant()).getByRole('listitem', { name });

function draftReply(draft: Partial<TripDraft>) {
  server.use(
    http.post(`${API_URL}/trip-drafts`, () =>
      HttpResponse.json({
        origin: 'Gdynia',
        destination: 'Toruń',
        passengers: 2,
        mode: null,
        preferences: null,
        missing_fields: [],
        parsed_by: 'llm',
        ...draft,
      } satisfies TripDraft),
    ),
  );
}

async function describeTrip(user: UserEvent, text: string, button = 'Plan my trip') {
  await user.type(within(assistant()).getByLabelText('Describe your trip'), text);
  await user.click(within(assistant()).getByRole('button', { name: button }));
}

describe('TripAssistant', () => {
  it('fills the form in manual mode without submitting it', async () => {
    let compared = false;
    server.use(
      http.post(`${API_URL}/comparisons`, () => {
        compared = true;
        return undefined;
      }),
    );
    const { user } = renderPage();

    await user.click(within(assistant()).getByRole('radio', { name: 'Manual' }));
    await describeTrip(user, 'jutro jadę z Gdyni do Torunia z żoną pociągiem', 'Fill in the form');

    expect(await within(assistant()).findByText(/The form is filled in/)).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toHaveValue('Gdynia');
    expect(screen.getByLabelText('To')).toHaveValue('Toruń');
    expect(screen.getByLabelText('Passengers')).toHaveValue(2);
    expect(screen.getByText('Where are you going?')).toBeInTheDocument();
    expect(compared).toBe(false);
  });

  it('shows the rules badge and stops for missing fields', async () => {
    draftReply({
      origin: null,
      destination: 'Zakopane',
      passengers: null,
      missing_fields: ['origin', 'passengers'],
      parsed_by: 'rules',
    });
    const { user } = renderPage();

    await describeTrip(user, 'weekend w Zakopanem');

    expect(
      await within(assistant()).findByText(
        "I couldn't find the starting point and how many of you are travelling — fill them in and press Compare.",
      ),
    ).toBeInTheDocument();
    expect(within(step(/Understanding your trip/)).getByText('rules')).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toHaveValue('');
    expect(screen.getByLabelText('To')).toHaveValue('Zakopane');
    expect(screen.getByLabelText('Passengers')).toHaveValue(1);
  });

  it('shows an error when the draft request fails', async () => {
    server.use(
      http.post(`${API_URL}/trip-drafts`, () =>
        HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'boom', details: null } },
          { status: 500 },
        ),
      ),
    );
    const { user } = renderPage();

    await describeTrip(user, 'from A to B');

    expect(await within(assistant()).findByRole('alert')).toHaveTextContent('Something went wrong');
    expect(step(/Understanding your trip: failed/)).toBeInTheDocument();
  });

  it('disables the button for empty text', () => {
    renderPage();

    expect(within(assistant()).getByRole('button', { name: 'Plan my trip' })).toBeDisabled();
  });

  it('fills the text from an example and counts characters', async () => {
    const { user } = renderPage();

    await user.click(
      within(assistant()).getByRole('button', {
        name: 'Cheapest way from Gdańsk to Kraków, solo',
      }),
    );

    const textarea = within(assistant()).getByLabelText('Describe your trip');
    expect(textarea).toHaveValue('Cheapest way from Gdańsk to Kraków, solo');
    expect(textarea).toHaveFocus();
    expect(within(assistant()).getByText('40/500 characters')).toBeInTheDocument();
  });
});
