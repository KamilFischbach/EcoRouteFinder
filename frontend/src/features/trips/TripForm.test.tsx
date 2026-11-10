import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TripForm } from './TripForm';
import { toFormValues } from './validation';
import { tripFixtures } from '@/test/handlers';

function setup(props: Partial<Parameters<typeof TripForm>[0]> = {}) {
  const onSubmit = vi.fn();
  const user = userEvent.setup();
  render(<TripForm submitLabel="Dodaj trasę" onSubmit={onSubmit} {...props} />);
  const submit = () => user.click(screen.getByRole('button', { name: 'Dodaj trasę' }));
  return { onSubmit, user, submit };
}

describe('TripForm', () => {
  it('shows required-field errors and does not submit an empty form', async () => {
    const { onSubmit, submit } = setup();

    await submit();

    expect(screen.getByText('Podaj miejsce startu.')).toBeInTheDocument();
    expect(screen.getByText('Podaj cel podróży.')).toBeInTheDocument();
    expect(screen.getByText('Podaj dystans.')).toBeInTheDocument();
    expect(screen.getByText('Wybierz środek transportu.')).toBeInTheDocument();
    expect(screen.getByLabelText('Skąd')).toHaveAttribute('aria-invalid', 'true');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('rejects non-positive distance and too many passengers', async () => {
    const { onSubmit, user, submit } = setup();

    await user.type(screen.getByLabelText('Dystans (km)'), '0');
    const passengers = screen.getByLabelText('Liczba osób');
    await user.clear(passengers);
    await user.type(passengers, '10');
    await submit();

    expect(screen.getByText('Dystans musi być liczbą większą od 0.')).toBeInTheDocument();
    expect(
      screen.getByText('Liczba osób musi być liczbą całkowitą od 1 do 9.'),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('clears an error as soon as the field becomes valid after a submit attempt', async () => {
    const { user, submit } = setup();

    await submit();
    await user.type(screen.getByLabelText('Skąd'), 'Kraków');

    expect(screen.queryByText('Podaj miejsce startu.')).not.toBeInTheDocument();
    expect(screen.getByText('Podaj cel podróży.')).toBeInTheDocument();
  });

  it('submits a normalized payload when the data is valid', async () => {
    const { onSubmit, user, submit } = setup();

    await user.type(screen.getByLabelText('Skąd'), '  Kraków ');
    await user.type(screen.getByLabelText('Dokąd'), 'Wrocław');
    await user.type(screen.getByLabelText('Dystans (km)'), '270,5');
    const passengers = screen.getByLabelText('Liczba osób');
    await user.clear(passengers);
    await user.type(passengers, '3');
    await user.click(screen.getByLabelText('Pociąg'));
    await submit();

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith({
      origin: 'Kraków',
      destination: 'Wrocław',
      distance_km: 270.5,
      passengers: 3,
      mode: 'train',
      note: null,
    });
  });

  it('prefills values when editing an existing trip', () => {
    const trip = tripFixtures[0]!;
    setup({ initialValues: toFormValues(trip) });

    expect(screen.getByLabelText('Skąd')).toHaveValue('Warszawa');
    expect(screen.getByLabelText('Dystans (km)')).toHaveValue('340');
    expect(screen.getByLabelText('Pociąg')).toBeChecked();
  });
});
