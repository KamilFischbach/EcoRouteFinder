import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import { statsFixture } from '@/test/handlers';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';
import type { Stats } from '@/types/stats';

import { DashboardPage } from './DashboardPage';

function LocationProbe() {
  return <p data-testid="location">{useLocation().search}</p>;
}

function renderDashboard(route = '/dashboard') {
  return renderWithProviders(
    <>
      <DashboardPage />
      <LocationProbe />
    </>,
    { route },
  );
}

function serveStats(stats: Stats) {
  server.use(http.get(`${API_URL}/stats`, () => HttpResponse.json(stats)));
}

function tile(name: string) {
  return screen.getByRole('region', { name });
}

describe('DashboardPage', () => {
  it('shows the KPIs, the level and a summary', async () => {
    renderDashboard();

    expect(
      await screen.findByText('You saved 38 kg more than in the previous 90 days.'),
    ).toBeVisible();
    expect(tile('CO₂ footprint')).toHaveTextContent('270 kg');
    expect(tile('CO₂ footprint')).toHaveTextContent('10% less than the previous 90 days, better');
    expect(tile('CO₂ saved vs petrol car')).toHaveTextContent('152.2 kg saved vs petrol car');
    expect(tile('Trips')).toHaveTextContent('23');
    expect(tile('Trips')).toHaveTextContent('3,150 km not driven');
    expect(tile('Eco-points')).toHaveTextContent('2,366');
    expect(screen.getByRole('heading', { name: 'Sapling' })).toBeInTheDocument();
    expect(screen.getByText(/1,634 pts to Tree/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Progress to Tree' })).toHaveValue(35);
    const levels = screen.getByRole('list', { name: 'All levels' });
    expect(within(levels).getAllByRole('listitem')).toHaveLength(5);
    expect(within(levels).getByText('Sapling').closest('li')).toHaveAttribute(
      'aria-current',
      'step',
    );
    expect(within(levels).getByText(', locked (4000 pts)')).toBeInTheDocument();
    expect(screen.getByText('Warszawa → Gdańsk')).toBeInTheDocument();
  });

  it('gives each chart a label and a text table with the same data', async () => {
    renderDashboard();

    await screen.findByRole('img', { name: /CO₂ footprint \(bars\)/ });
    expect(screen.getByRole('img', { name: /by transport mode/ })).toBeInTheDocument();
    const timeline = screen.getByRole('table', { name: /CO₂ per week/ });
    expect(within(timeline).getAllByRole('row')).toHaveLength(4);
    expect(
      within(timeline).getByRole('rowheader', { name: 'Week of 9 Nov 2026' }),
    ).toBeInTheDocument();
    const modes = screen.getByRole('table', { name: /by transport mode/ });
    expect(within(modes).getByRole('rowheader', { name: 'Petrol car' })).toBeInTheDocument();
  });

  it('loads another range and puts it in the URL', async () => {
    const requested: string[] = [];
    server.use(
      http.get(`${API_URL}/stats`, ({ request }) => {
        const range = new URL(request.url).searchParams.get('range') ?? '';
        requested.push(range);
        return HttpResponse.json({ ...statsFixture, range });
      }),
    );
    const { user } = renderDashboard();
    await screen.findByText('You saved 38 kg more than in the previous 90 days.');

    await user.click(screen.getByRole('radio', { name: '30 days' }));

    expect(
      await screen.findByText('You saved 38 kg more than in the previous 30 days.'),
    ).toBeInTheDocument();
    expect(requested).toEqual(['90d', '30d']);
    expect(screen.getByTestId('location')).toHaveTextContent('?range=30d');
    expect(screen.getByRole('radio', { name: '30 days' })).toBeChecked();
  });

  it('reads the range from the URL', async () => {
    renderDashboard('/dashboard?range=12m');

    expect(await screen.findByRole('radio', { name: '12 months' })).toBeChecked();
    expect(
      await screen.findByText('You saved 38 kg more than in the previous 12 months.'),
    ).toBeInTheDocument();
  });

  it('words negative savings as extra emissions', async () => {
    serveStats({
      ...statsFixture,
      totals: { ...statsFixture.totals, co2_saved_kg: -12 },
    });
    renderDashboard();

    expect(await screen.findByText('12 kg more than going by petrol car')).toBeInTheDocument();
    expect(tile('CO₂ saved vs petrol car')).not.toHaveTextContent('kg saved');
  });

  it('shows an empty state with a link to Compare when there are no trips', async () => {
    serveStats({
      ...statsFixture,
      totals: { ...statsFixture.totals, trips: 0 },
      by_mode: [],
      best_trip: null,
    });
    renderDashboard();

    expect(
      await screen.findByText('Save a trip from the comparison page to see your footprint here.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Compare a route' })).toHaveAttribute(
      'href',
      '/compare',
    );
  });

  it('shows an error with Try again, which reloads the data', async () => {
    let calls = 0;
    server.use(
      http.get(`${API_URL}/stats`, () => {
        calls += 1;
        if (calls === 1) {
          return HttpResponse.json(
            { error: { code: 'INTERNAL_ERROR', message: 'Boom', details: null } },
            { status: 500 },
          );
        }
        return HttpResponse.json(statsFixture);
      }),
    );
    const { user } = renderDashboard();

    const alert = await screen.findByRole('alert');
    await user.click(within(alert).getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText(/You saved 38 kg more/)).toBeInTheDocument();
  });
});
