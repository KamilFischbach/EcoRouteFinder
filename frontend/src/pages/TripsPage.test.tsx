import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import { statsKeys } from '@/features/dashboard/useStats';
import { resetTripDb, statsFixture } from '@/test/handlers';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';

import { TripsPage } from './TripsPage';

function getRows() {
  const table = screen.getByRole('table', { name: 'Saved trips' });
  // First row is the header.
  return within(table).getAllByRole('row').slice(1);
}

describe('TripsPage list', () => {
  it('shows a loading state, then renders trips from the API', async () => {
    renderWithProviders(<TripsPage />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading trips…');

    expect(await screen.findByText('Warszawa → Gdańsk')).toBeInTheDocument();
    expect(screen.getByText('Kraków → Zakopane')).toBeInTheDocument();
    expect(getRows()).toHaveLength(2);
    expect(screen.getByText('Weekend by the sea')).toBeInTheDocument();
  });

  it('shows an empty state when there are no trips', async () => {
    resetTripDb([]);
    renderWithProviders(<TripsPage />);

    expect(await screen.findByText('You have no saved trips yet')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows an error state with retry when the API fails', async () => {
    server.use(
      http.get(`${API_URL}/trips`, () =>
        HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'boom', details: null } },
          { status: 500 },
        ),
      ),
    );
    renderWithProviders(<TripsPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load data');
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('filters trips by transport mode', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.selectOptions(screen.getByLabelText('Filter by transport mode'), 'car_ev');

    await waitFor(() => expect(screen.queryByText('Warszawa → Gdańsk')).not.toBeInTheDocument());
    expect(getRows()).toHaveLength(1);
  });

  it('adds a new trip to the list', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.type(screen.getByLabelText('From'), 'Poznań');
    await user.type(screen.getByLabelText('To'), 'Berlin');
    await user.type(screen.getByLabelText('Distance (km)'), '270');
    await user.click(screen.getByLabelText('Bike'));
    await user.click(screen.getByRole('button', { name: 'Add trip' }));

    expect(await screen.findByText('Poznań → Berlin')).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toHaveValue('');
  });

  it('deletes a trip after confirmation', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.click(screen.getByRole('button', { name: 'Delete trip Warszawa → Gdańsk' }));
    const dialog = screen.getByRole('alertdialog', { name: 'Delete this trip?' });
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Warszawa → Gdańsk')).not.toBeInTheDocument());
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(getRows()).toHaveLength(1);
  });

  it('marks the dashboard statistics as stale after a trip is deleted', async () => {
    const { user, queryClient } = renderWithProviders(<TripsPage />);
    queryClient.setQueryData(statsKeys.detail('90d'), statsFixture);
    await screen.findByText('Warszawa → Gdańsk');

    await user.click(screen.getByRole('button', { name: 'Delete trip Warszawa → Gdańsk' }));
    const dialog = screen.getByRole('alertdialog', { name: 'Delete this trip?' });
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    await waitFor(() =>
      expect(queryClient.getQueryState(statsKeys.detail('90d'))?.isInvalidated).toBe(true),
    );
  });

  it('keeps the trip when deletion is cancelled', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.click(screen.getByRole('button', { name: 'Delete trip Warszawa → Gdańsk' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(getRows()).toHaveLength(2);
  });
});
