import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { API_URL } from '@/api/client';
import { resetTripDb } from '@/test/handlers';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';

import { TripsPage } from './TripsPage';

function getRows() {
  const table = screen.getByRole('table', { name: 'Zapisane trasy' });
  // First row is the header.
  return within(table).getAllByRole('row').slice(1);
}

describe('TripsPage list', () => {
  it('shows a loading state, then renders trips from the API', async () => {
    renderWithProviders(<TripsPage />);

    expect(screen.getByRole('status')).toHaveTextContent('Ładowanie tras…');

    expect(await screen.findByText('Warszawa → Gdańsk')).toBeInTheDocument();
    expect(screen.getByText('Kraków → Zakopane')).toBeInTheDocument();
    expect(getRows()).toHaveLength(2);
    expect(screen.getByText('Weekend nad morzem')).toBeInTheDocument();
  });

  it('shows an empty state when there are no trips', async () => {
    resetTripDb([]);
    renderWithProviders(<TripsPage />);

    expect(await screen.findByText('Nie masz jeszcze zapisanych tras')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows an error state with retry when the API fails', async () => {
    server.use(
      http.get(`${API_URL}/trips`, () =>
        HttpResponse.json(
          { error: { code: 'internal_error', message: 'boom', details: null } },
          { status: 500 },
        ),
      ),
    );
    renderWithProviders(<TripsPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Nie udało się wczytać danych');
    expect(screen.getByRole('button', { name: 'Spróbuj ponownie' })).toBeInTheDocument();
  });

  it('filters trips by transport mode', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.selectOptions(screen.getByLabelText('Filtruj po środku transportu'), 'car_ev');

    await waitFor(() => expect(screen.queryByText('Warszawa → Gdańsk')).not.toBeInTheDocument());
    expect(getRows()).toHaveLength(1);
  });

  it('adds a new trip to the list', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.type(screen.getByLabelText('Skąd'), 'Poznań');
    await user.type(screen.getByLabelText('Dokąd'), 'Berlin');
    await user.type(screen.getByLabelText('Dystans (km)'), '270');
    await user.click(screen.getByLabelText('Rower'));
    await user.click(screen.getByRole('button', { name: 'Dodaj trasę' }));

    expect(await screen.findByText('Poznań → Berlin')).toBeInTheDocument();
    expect(screen.getByLabelText('Skąd')).toHaveValue('');
  });

  it('deletes a trip after confirmation', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.click(screen.getByRole('button', { name: 'Usuń trasę Warszawa → Gdańsk' }));
    const dialog = screen.getByRole('alertdialog', { name: 'Usunąć trasę?' });
    await user.click(within(dialog).getByRole('button', { name: 'Usuń' }));

    await waitFor(() => expect(screen.queryByText('Warszawa → Gdańsk')).not.toBeInTheDocument());
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(getRows()).toHaveLength(1);
  });

  it('keeps the trip when deletion is cancelled', async () => {
    const { user } = renderWithProviders(<TripsPage />);
    await screen.findByText('Warszawa → Gdańsk');

    await user.click(screen.getByRole('button', { name: 'Usuń trasę Warszawa → Gdańsk' }));
    await user.click(screen.getByRole('button', { name: 'Anuluj' }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(getRows()).toHaveLength(2);
  });
});
