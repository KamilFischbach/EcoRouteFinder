import { screen, waitFor, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import { ComparePage } from '@/pages/ComparePage';
import { adviceFixture, resetComparisonDb, savedComparison } from '@/test/handlers';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';
import type { TripDraft } from '@/types/tripDraft';

import { ASSISTANT_MODE_KEY } from './assistantMode';

function LocationProbe() {
  return <span data-testid="location">{useLocation().pathname}</span>;
}

function renderPage(route = '/compare') {
  return renderWithProviders(
    <>
      <LocationProbe />
      <Routes>
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/compare/:id" element={<ComparePage />} />
        <Route path="*" element={null} />
      </Routes>
    </>,
    { route },
  );
}

const assistant = () => screen.getByRole('region', { name: 'Trip assistant' });
const step = (name: RegExp) => within(assistant()).getByRole('listitem', { name });
const card = (name: string) =>
  within(screen.getByRole('list', { name: 'Transport options' })).getByRole('listitem', { name });

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

const advisor = () => screen.getByRole('region', { name: 'EcoAdvisor' });
// The card appears once the comparison is saved, so wait for it first.
const findAdvisor = () => screen.findByRole('region', { name: 'EcoAdvisor' });

/** Records request bodies (the handlers below fall through to the defaults). */
function recordBodies() {
  const sent: { comparisons: unknown[]; advice: unknown[] } = { comparisons: [], advice: [] };
  server.use(
    http.post(`${API_URL}/comparisons`, async ({ request }) => {
      sent.comparisons.push(await request.clone().json());
      return undefined;
    }),
    http.post(`${API_URL}/comparisons/:id/advice`, async ({ request }) => {
      sent.advice.push(await request.clone().json());
      return undefined;
    }),
  );
  return sent;
}

const SKI_TEXT =
  'I want to go skiing with my girlfriend from Tczew to Karpacz. We have ski equipment and comfort matters to us.';

describe('TripAssistant auto mode', () => {
  it('runs every step: parse, compare, navigate, advise', async () => {
    draftReply({
      origin: 'Tczew',
      destination: 'Karpacz',
      preferences: 'ski equipment, comfort matters',
    });
    const sent = recordBodies();
    const { user } = renderPage();

    await describeTrip(user, SKI_TEXT);

    expect(await within(await findAdvisor()).findByText(adviceFixture.summary)).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('/compare/1');
    expect(screen.getByRole('heading', { name: 'Tczew → Karpacz' })).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Transport options' })).toBeInTheDocument();
    expect(within(step(/Understanding your trip: done/)).getByText('AI')).toBeInTheDocument();
    expect(step(/Comparing 6 ways to travel: done/)).toBeInTheDocument();
    expect(step(/Asking EcoAdvisor: done/)).toBeInTheDocument();
    expect(sent.comparisons).toEqual([{ origin: 'Tczew', destination: 'Karpacz', passengers: 2 }]);
    expect(sent.advice).toEqual([{ preferences: 'ski equipment, comfort matters' }]);
    // The form shows what was used, so the user can tweak it and compare again.
    expect(screen.getByLabelText('What matters to you?')).toHaveValue(
      'ski equipment, comfort matters',
    );
    expect(within(card('Coach')).getByText('EcoAdvisor pick')).toBeInTheDocument();
  });

  it('shows the results before the advice arrives', async () => {
    let release: () => void = () => undefined;
    const adviceGate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post(`${API_URL}/comparisons/:id/advice`, async () => {
        await adviceGate;
        return undefined;
      }),
    );
    const { user } = renderPage();

    await describeTrip(user, 'z Gdyni do Torunia z żoną');

    expect(await screen.findByRole('list', { name: 'Transport options' })).toBeInTheDocument();
    expect(
      within(advisor()).getByText('EcoAdvisor is thinking… (local model, can take ~20 s)'),
    ).toBeInTheDocument();
    expect(step(/Asking EcoAdvisor: in progress/)).toBeInTheDocument();

    release();

    expect(await within(await findAdvisor()).findByText(adviceFixture.summary)).toBeInTheDocument();
  });

  it('sends with Ctrl+Enter', async () => {
    const { user } = renderPage();

    await user.type(within(assistant()).getByLabelText('Describe your trip'), 'z Gdyni do Torunia');
    await user.keyboard('{Control>}{Enter}{/Control}');

    expect(await within(await findAdvisor()).findByText(adviceFixture.summary)).toBeInTheDocument();
  });

  it('stops when a field is missing, fills the rest and focuses the gap', async () => {
    draftReply({
      origin: 'Gdynia',
      destination: null,
      preferences: 'cheapest option',
      missing_fields: ['destination'],
      parsed_by: 'rules',
    });
    const sent = recordBodies();
    const { user } = renderPage();

    await describeTrip(user, 'cheapest trip from Gdynia for 2');

    expect(
      await within(assistant()).findByText(
        "I couldn't find the destination — fill it in and press Compare.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toHaveValue('Gdynia');
    expect(screen.getByLabelText('Passengers')).toHaveValue(2);
    expect(screen.getByLabelText('What matters to you?')).toHaveValue('cheapest option');
    expect(screen.getByLabelText('To')).toHaveValue('');
    expect(screen.getByLabelText('To')).toHaveFocus();
    expect(step(/Comparing 6 ways to travel: waiting/)).toBeInTheDocument();
    expect(sent.comparisons).toEqual([]);
    expect(screen.getByText('Where are you going?')).toBeInTheDocument();

    // Filling the gap and pressing Compare carries on, advice included.
    await user.type(screen.getByLabelText('To'), 'Toruń');
    await user.click(screen.getByRole('button', { name: 'Compare' }));

    expect(await within(await findAdvisor()).findByText(adviceFixture.summary)).toBeInTheDocument();
    expect(sent.advice).toEqual([{ preferences: 'cheapest option' }]);
    expect(step(/Understanding your trip: done/)).toBeInTheDocument();
  });
});

describe('TripAssistant manual mode', () => {
  it('fills the form with preferences and does not compare', async () => {
    draftReply({ preferences: 'large suitcase' });
    const sent = recordBodies();
    const { user } = renderPage();

    await user.click(within(assistant()).getByRole('radio', { name: 'Manual' }));
    await describeTrip(user, 'z Gdyni do Torunia z żoną, mamy dużą walizkę', 'Fill in the form');

    expect(await screen.findByLabelText('What matters to you?')).toHaveValue('large suitcase');
    await waitFor(() => expect(screen.getByLabelText('From')).toHaveValue('Gdynia'));
    expect(screen.getByRole('form', { name: 'Compare form' })).toHaveClass('animate-form-filled');
    expect(step(/Comparing 6 ways to travel: waiting/)).toBeInTheDocument();
    expect(sent.comparisons).toEqual([]);
    expect(sent.advice).toEqual([]);
  });

  it('remembers the chosen mode', async () => {
    const { user, unmount } = renderPage();

    await user.click(within(assistant()).getByRole('radio', { name: 'Manual' }));

    expect(window.localStorage.getItem(ASSISTANT_MODE_KEY)).toBe('manual');
    unmount();
    renderPage();
    expect(within(assistant()).getByRole('radio', { name: 'Manual' })).toBeChecked();
    expect(within(assistant()).getByRole('button', { name: 'Fill in the form' })).toBeDisabled(); // no text yet
    expect(screen.getByText(/Only fills in the form below/)).toBeInTheDocument();
  });

  it('switches mode with the arrow keys', async () => {
    const { user } = renderPage();

    within(assistant()).getByRole('radio', { name: 'Auto' }).focus();
    await user.keyboard('{ArrowRight}');

    expect(within(assistant()).getByRole('radio', { name: 'Manual' })).toBeChecked();
    expect(within(assistant()).getByRole('radio', { name: 'Manual' })).toHaveFocus();
  });
});

describe('Compare form and EcoAdvisor', () => {
  async function compareByHand(user: UserEvent, preferences: string) {
    await user.type(screen.getByLabelText('From'), 'Warszawa');
    await user.type(screen.getByLabelText('To'), 'Kraków');
    await user.type(screen.getByLabelText('What matters to you?'), preferences);
    await user.click(screen.getByRole('button', { name: 'Compare' }));
  }

  it('asks EcoAdvisor on its own after a manual comparison', async () => {
    const sent = recordBodies();
    const { user } = renderPage();

    await compareByHand(user, 'cheapest please');

    expect(await within(await findAdvisor()).findByText(adviceFixture.summary)).toBeInTheDocument();
    expect(sent.comparisons).toEqual([
      { origin: 'Warszawa', destination: 'Kraków', passengers: 1 },
    ]);
    expect(sent.advice).toEqual([{ preferences: 'cheapest please' }]);
    expect(step(/Understanding your trip: skipped/)).toBeInTheDocument();
    expect(step(/Asking EcoAdvisor: done/)).toBeInTheDocument();
    // The box is emptied for the next question once the answer is there.
    expect(within(advisor()).getByLabelText(/preferences/i)).toHaveValue('');
    expect(within(advisor()).getByLabelText(/preferences/i)).toHaveAttribute(
      'placeholder',
      expect.stringContaining('e.g.'),
    );
  });

  it('keeps the results when advice fails and recovers with Try again', async () => {
    let calls = 0;
    server.use(
      http.post(`${API_URL}/comparisons/:id/advice`, () => {
        calls += 1;
        if (calls > 1) return undefined;
        return HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'boom', details: null } },
          { status: 500 },
        );
      }),
    );
    const { user } = renderPage();

    await compareByHand(user, 'comfort');

    expect(await within(await findAdvisor()).findByRole('alert')).toHaveTextContent(
      "EcoAdvisor couldn't answer: Something went wrong",
    );
    expect(screen.getByRole('heading', { name: 'Warszawa → Kraków' })).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Transport options' })).toBeInTheDocument();
    expect(step(/Asking EcoAdvisor: failed/)).toBeInTheDocument();

    await user.click(within(advisor()).getByRole('button', { name: 'Try again' }));

    expect(await within(await findAdvisor()).findByText(adviceFixture.summary)).toBeInTheDocument();
    expect(within(advisor()).queryByRole('alert')).not.toBeInTheDocument();
    expect(step(/Asking EcoAdvisor: done/)).toBeInTheDocument();
    expect(calls).toBe(2);
  });

  it('does not ask EcoAdvisor when opening a saved comparison', async () => {
    resetComparisonDb([savedComparison(4, '2026-11-09T10:00:00Z')]);
    const sent = recordBodies();
    renderPage('/compare/4');

    expect(await screen.findByRole('heading', { name: 'Warszawa → Kraków' })).toBeInTheDocument();
    expect(within(advisor()).getByRole('button', { name: 'Ask EcoAdvisor' })).toBeInTheDocument();
    expect(sent.advice).toEqual([]);
  });
});
