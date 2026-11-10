import { screen, waitFor, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import {
  adviceFixture,
  getComparisonDb,
  getTripDb,
  resetComparisonDb,
  savedComparison,
} from '@/test/handlers';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';
import type { ComparisonInput } from '@/types/comparison';

import { ComparePage } from './ComparePage';

async function fillAndSubmit(user: UserEvent, destination = 'Kraków') {
  await user.type(screen.getByLabelText('From'), 'Warszawa');
  await user.type(screen.getByLabelText('To'), destination);
  const passengers = screen.getByLabelText('Passengers');
  await user.clear(passengers);
  await user.type(passengers, '2');
  await user.click(screen.getByRole('button', { name: 'Compare' }));
}

/** Renders the compare routes like App does, so navigation to /compare/:id works. */
function renderPage(route = '/compare') {
  return renderWithProviders(
    <Routes>
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/compare/:id" element={<ComparePage />} />
    </Routes>,
    { route },
  );
}

function card(name: string) {
  const list = screen.getByRole('list', { name: 'Transport options' });
  return within(list).getByRole('listitem', { name });
}

describe('ComparePage', () => {
  it('shows a start state before the first search', () => {
    renderPage();

    expect(screen.getByText('Where are you going?')).toBeInTheDocument();
  });

  it('validates the form before sending', async () => {
    const { user } = renderPage();

    await user.click(screen.getByRole('button', { name: 'Compare' }));

    expect(screen.getByText('Enter a starting point.')).toBeInTheDocument();
    expect(screen.getByText('Enter a destination.')).toBeInTheDocument();
  });

  it('submits the form and renders sorted cards with highlight badges', async () => {
    let sent: ComparisonInput | undefined;
    server.use(
      http.post(`${API_URL}/comparisons`, async ({ request }) => {
        sent = (await request.clone().json()) as ComparisonInput;
        return undefined; // fall through to the default handler
      }),
    );
    const { user } = renderPage();

    await fillAndSubmit(user);

    expect(await screen.findByRole('heading', { name: 'Warszawa → Kraków' })).toBeInTheDocument();
    expect(sent).toEqual({ origin: 'Warszawa', destination: 'Kraków', passengers: 2 });

    const train = card('Train');
    expect(within(train).getByText('Greenest')).toBeInTheDocument();
    expect(within(train).getByText('38.9 kg CO₂ less than driving alone')).toBeInTheDocument();
    const ev = card('Electric car');
    expect(within(ev).getByText('Fastest')).toBeInTheDocument();
    expect(within(ev).getByText('Cheapest')).toBeInTheDocument();

    const plane = card('Plane');
    expect(within(plane).getByText('Not practical')).toBeInTheDocument();
    expect(within(plane).getByText('Not worth flying under 300 km.')).toBeInTheDocument();
    expect(within(plane).getByText('10 kg CO₂ more than driving alone')).toBeInTheDocument();

    // Practical options first (by CO2), impractical ones last.
    const names = within(screen.getByRole('list', { name: 'Transport options' }))
      .getAllByRole('listitem')
      .map((item) => item.getAttribute('aria-label'));
    expect(names).toEqual(['Train', 'Coach', 'Electric car', 'Petrol car', 'Bike', 'Plane']);
  });

  it('sends the manual distance from the Advanced section', async () => {
    let sent: ComparisonInput | undefined;
    server.use(
      http.post(`${API_URL}/comparisons`, async ({ request }) => {
        sent = (await request.clone().json()) as ComparisonInput;
        return undefined;
      }),
    );
    const { user } = renderPage();

    await user.click(screen.getByRole('button', { name: 'Advanced' }));
    await user.type(screen.getByLabelText('Distance (km, optional)'), '12,5');
    await fillAndSubmit(user);

    await screen.findByRole('heading', { name: 'Warszawa → Kraków' });
    expect(sent?.distance_km).toBe(12.5);
  });

  it('shows a readable message for an unknown place', async () => {
    server.use(
      http.post(`${API_URL}/comparisons`, () =>
        HttpResponse.json(
          {
            error: {
              code: 'UNKNOWN_PLACE',
              message: "Could not find a place called 'Atlantyda'",
              details: { place: 'Atlantyda' },
            },
          },
          { status: 422 },
        ),
      ),
    );
    const { user } = renderPage();

    await fillAndSubmit(user, 'Atlantyda');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent("Couldn't compare this route");
    expect(alert).toHaveTextContent('We couldn\'t find "Atlantyda"');
  });

  it('saves a trip from a card', async () => {
    const { user } = renderPage();
    await fillAndSubmit(user);
    await screen.findByRole('heading', { name: 'Warszawa → Kraków' });

    await user.click(screen.getByRole('button', { name: 'Save trip by Train' }));

    expect(await within(card('Train')).findByRole('status')).toHaveTextContent(
      'Saved to your trips',
    );
    await waitFor(() =>
      expect(getTripDb()[0]).toMatchObject({
        origin: 'Warszawa',
        destination: 'Kraków',
        distance_km: 305.3,
        passengers: 2,
        mode: 'train',
      }),
    );
  });
});

describe('ComparePage history', () => {
  const history = () => screen.findByRole('list', { name: 'Recent comparisons' });

  it('shows an empty state when there are no comparisons', async () => {
    renderPage();

    expect(await screen.findByText(/No comparisons yet/)).toBeInTheDocument();
  });

  it('lists recent comparisons with route, greenest mode and savings', async () => {
    resetComparisonDb([
      savedComparison(2, new Date(Date.now() - 2 * 3_600_000).toISOString(), 'Gdańsk', 'Sopot'),
      savedComparison(1, '2026-10-01T10:00:00Z'),
    ]);
    renderPage();

    const rows = within(await history()).getAllByRole('link');
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining('Gdańsk → Sopot'),
      expect.stringContaining('Warszawa → Kraków'),
    ]);
    expect(rows[0]).toHaveTextContent('2 h ago');
    expect(rows[0]).toHaveTextContent('Train');
    // Solo petrol car 48.37 kg - train 9.44 kg.
    expect(rows[0]).toHaveTextContent('saves 38.9 kg CO₂');
  });

  it('opens a saved comparison from its snapshot', async () => {
    resetComparisonDb([savedComparison(7, '2026-11-09T10:00:00Z', 'Łódź', 'Poznań')]);
    let posted = false;
    server.use(
      http.post(`${API_URL}/comparisons`, () => {
        posted = true;
        return undefined;
      }),
    );
    const { user } = renderPage();

    await user.click(within(await history()).getByRole('link', { name: /Łódź → Poznań/ }));

    expect(await screen.findByRole('heading', { name: 'Łódź → Poznań' })).toBeInTheDocument();
    expect(within(card('Train')).getByText('Greenest')).toBeInTheDocument();
    expect(posted).toBe(false);
  });

  it('loads a saved comparison directly from its URL', async () => {
    resetComparisonDb([savedComparison(7, '2026-11-09T10:00:00Z', 'Łódź', 'Poznań')]);
    renderPage('/compare/7');

    expect(await screen.findByRole('heading', { name: 'Łódź → Poznań' })).toBeInTheDocument();
  });

  it('shows not found for a missing comparison', async () => {
    renderPage('/compare/99');

    expect(await screen.findByText('Comparison not found')).toBeInTheDocument();
  });

  it('adds a new comparison to the history and opens it', async () => {
    const { user } = renderPage();
    await screen.findByText(/No comparisons yet/);

    await fillAndSubmit(user);

    expect(await screen.findByRole('heading', { name: 'Warszawa → Kraków' })).toBeInTheDocument();
    expect(
      within(await history()).getByRole('link', { name: /Warszawa → Kraków/ }),
    ).toHaveAttribute('aria-current', 'page');
  });

  it('deletes a comparison after confirmation', async () => {
    resetComparisonDb([
      savedComparison(2, '2026-11-09T10:00:00Z', 'Gdańsk', 'Sopot'),
      savedComparison(1, '2026-11-08T10:00:00Z'),
    ]);
    const { user } = renderPage();
    await history();

    await user.click(screen.getByRole('button', { name: 'Delete comparison Gdańsk → Sopot' }));
    const dialog = screen.getByRole('alertdialog', { name: 'Delete this comparison?' });
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Gdańsk → Sopot')).not.toBeInTheDocument());
    expect(getComparisonDb().map((c) => c.id)).toEqual([1]);
  });
});

describe('ComparePage describe your trip', () => {
  async function describeTrip(user: UserEvent, text: string) {
    await user.type(screen.getByLabelText('Describe your trip'), text);
    await user.click(screen.getByRole('button', { name: 'Fill in with AI' }));
  }

  it('fills the form from the AI draft without submitting it', async () => {
    let compared = false;
    server.use(
      http.post(`${API_URL}/comparisons`, () => {
        compared = true;
        return undefined;
      }),
    );
    const { user } = renderPage();

    await describeTrip(user, 'jutro jadę z Gdyni do Torunia z żoną pociągiem');

    expect(await screen.findByText('Filled by AI')).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toHaveValue('Gdynia');
    expect(screen.getByLabelText('To')).toHaveValue('Toruń');
    expect(screen.getByLabelText('Passengers')).toHaveValue(2);
    expect(screen.getByText('You mentioned: Train.')).toBeInTheDocument();
    expect(screen.getByText('Where are you going?')).toBeInTheDocument();
    expect(compared).toBe(false);
  });

  it('shows the rules badge and missing fields', async () => {
    server.use(
      http.post(`${API_URL}/trip-drafts`, () =>
        HttpResponse.json({
          origin: null,
          destination: 'Zakopane',
          passengers: null,
          mode: null,
          preferences: null,
          missing_fields: ['origin', 'passengers'],
          parsed_by: 'rules',
        }),
      ),
    );
    const { user } = renderPage();

    await describeTrip(user, 'weekend w Zakopanem');

    expect(await screen.findByText('Filled by rules')).toBeInTheDocument();
    expect(screen.getByText(/Not found in your text: From, Passengers/)).toBeInTheDocument();
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

    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong');
  });

  it('disables the fill-in button for empty text', () => {
    renderPage();

    expect(screen.getByRole('button', { name: 'Fill in with AI' })).toBeDisabled();
  });
});

describe('ComparePage EcoAdvisor', () => {
  const advisor = () => screen.getByRole('region', { name: 'EcoAdvisor' });

  async function openSaved(comparison = savedComparison(3, '2026-11-09T10:00:00Z')) {
    resetComparisonDb([comparison]);
    const view = renderPage('/compare/3');
    await screen.findByRole('heading', { name: 'Warszawa → Kraków' });
    return view;
  }

  it('asks the AI advisor and highlights the recommended card', async () => {
    let sent: unknown;
    server.use(
      http.post(`${API_URL}/comparisons/:id/advice`, async ({ request }) => {
        sent = await request.clone().json();
        return undefined;
      }),
    );
    const { user } = await openSaved();

    await user.type(within(advisor()).getByLabelText(/preferences/i), 'cheapest please');
    await user.click(within(advisor()).getByRole('button', { name: 'Ask EcoAdvisor' }));

    expect(await within(advisor()).findByText('AI · qwen2.5:7b')).toBeInTheDocument();
    expect(sent).toEqual({ preferences: 'cheapest please' });
    expect(within(advisor()).getByText(adviceFixture.summary)).toBeInTheDocument();
    expect(within(advisor()).getByText('11.8 kg CO₂ per person')).toBeInTheDocument();
    expect(within(advisor()).getByText(/Kraków: 3 °C, overcast/)).toBeInTheDocument();
    expect(within(card('Coach')).getByText('EcoAdvisor pick')).toBeInTheDocument();
    expect(within(card('Train')).queryByText('EcoAdvisor pick')).not.toBeInTheDocument();
    expect(within(advisor()).getByRole('button', { name: 'Ask again' })).toBeInTheDocument();
  });

  it('shows the rule-based badge when AI is offline', async () => {
    server.use(
      http.post(`${API_URL}/comparisons/:id/advice`, () =>
        HttpResponse.json({
          ...adviceFixture,
          recommended_mode: 'train',
          used_llm: false,
          model: null,
          tool_trace: [],
        }),
      ),
    );
    const { user } = await openSaved();

    await user.click(within(advisor()).getByRole('button', { name: 'Ask EcoAdvisor' }));

    expect(await within(advisor()).findByText('Rule-based (AI offline)')).toBeInTheDocument();
    expect(within(card('Train')).getByText('EcoAdvisor pick')).toBeInTheDocument();
    await user.click(within(advisor()).getByText('How I got this'));
    expect(within(advisor()).getByText(/No extra tools were needed/)).toBeInTheDocument();
  });

  it('shows an error when the advice request fails', async () => {
    server.use(
      http.post(`${API_URL}/comparisons/:id/advice`, () =>
        HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'boom', details: null } },
          { status: 500 },
        ),
      ),
    );
    const { user } = await openSaved();

    await user.click(within(advisor()).getByRole('button', { name: 'Ask EcoAdvisor' }));

    expect(await within(advisor()).findByRole('alert')).toHaveTextContent('Something went wrong');
  });

  it('shows saved advice immediately when opening a comparison', async () => {
    let asked = false;
    server.use(
      http.post(`${API_URL}/comparisons/:id/advice`, () => {
        asked = true;
        return undefined;
      }),
    );
    const { user } = await openSaved({
      ...savedComparison(3, '2026-11-09T10:00:00Z'),
      advice: adviceFixture,
    });

    expect(within(advisor()).getByText(adviceFixture.summary)).toBeInTheDocument();
    expect(within(card('Coach')).getByText('EcoAdvisor pick')).toBeInTheDocument();
    await user.click(within(advisor()).getByText('How I got this'));
    expect(within(advisor()).getByRole('list', { name: 'Tool calls' })).toHaveTextContent(
      'get_weather({"location":"Kraków"})',
    );
    expect(asked).toBe(false);
  });
});
