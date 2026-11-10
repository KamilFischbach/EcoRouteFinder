import { screen, waitFor, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import { getTripDb } from '@/test/handlers';
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

function card(name: string) {
  const list = screen.getByRole('list', { name: 'Transport options' });
  return within(list).getByRole('listitem', { name });
}

describe('ComparePage', () => {
  it('shows a start state before the first search', () => {
    renderWithProviders(<ComparePage />);

    expect(screen.getByText('Where are you going?')).toBeInTheDocument();
  });

  it('validates the form before sending', async () => {
    const { user } = renderWithProviders(<ComparePage />);

    await user.click(screen.getByRole('button', { name: 'Compare' }));

    expect(screen.getByText('Enter a starting point.')).toBeInTheDocument();
    expect(screen.getByText('Enter a destination.')).toBeInTheDocument();
  });

  it('submits the form and renders sorted cards with highlight badges', async () => {
    let sent: ComparisonInput | undefined;
    server.use(
      http.post(`${API_URL}/comparisons`, async ({ request }) => {
        sent = (await request.json()) as ComparisonInput;
        return undefined; // fall through to the default handler
      }),
    );
    const { user } = renderWithProviders(<ComparePage />);

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
        sent = (await request.json()) as ComparisonInput;
        return undefined;
      }),
    );
    const { user } = renderWithProviders(<ComparePage />);

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
    const { user } = renderWithProviders(<ComparePage />);

    await fillAndSubmit(user, 'Atlantyda');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent("Couldn't compare this route");
    expect(alert).toHaveTextContent('We couldn\'t find "Atlantyda"');
  });

  it('saves a trip from a card', async () => {
    const { user } = renderWithProviders(<ComparePage />);
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
