import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TripForm } from './TripForm';
import { toFormValues } from './validation';
import { tripFixtures } from '@/test/handlers';

function setup(props: Partial<Parameters<typeof TripForm>[0]> = {}) {
  const onSubmit = vi.fn();
  const user = userEvent.setup();
  render(<TripForm submitLabel="Add trip" onSubmit={onSubmit} {...props} />);
  const submit = () => user.click(screen.getByRole('button', { name: 'Add trip' }));
  return { onSubmit, user, submit };
}

describe('TripForm', () => {
  it('shows required-field errors and does not submit an empty form', async () => {
    const { onSubmit, submit } = setup();

    await submit();

    expect(screen.getByText('Enter a starting point.')).toBeInTheDocument();
    expect(screen.getByText('Enter a destination.')).toBeInTheDocument();
    expect(screen.getByText('Enter a distance.')).toBeInTheDocument();
    expect(screen.getByText('Choose a transport mode.')).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toHaveAttribute('aria-invalid', 'true');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('rejects non-positive distance and too many passengers', async () => {
    const { onSubmit, user, submit } = setup();

    await user.type(screen.getByLabelText('Distance (km)'), '0');
    const passengers = screen.getByLabelText('Passengers');
    await user.clear(passengers);
    await user.type(passengers, '10');
    await submit();

    expect(screen.getByText('Distance must be a number greater than 0.')).toBeInTheDocument();
    expect(screen.getByText('Passengers must be a whole number from 1 to 9.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('clears an error as soon as the field becomes valid after a submit attempt', async () => {
    const { user, submit } = setup();

    await submit();
    await user.type(screen.getByLabelText('From'), 'Kraków');

    expect(screen.queryByText('Enter a starting point.')).not.toBeInTheDocument();
    expect(screen.getByText('Enter a destination.')).toBeInTheDocument();
  });

  it('submits a normalized payload when the data is valid', async () => {
    const { onSubmit, user, submit } = setup();

    await user.type(screen.getByLabelText('From'), '  Kraków ');
    await user.type(screen.getByLabelText('To'), 'Wrocław');
    await user.type(screen.getByLabelText('Distance (km)'), '270,5');
    const passengers = screen.getByLabelText('Passengers');
    await user.clear(passengers);
    await user.type(passengers, '3');
    await user.click(screen.getByLabelText('Train'));
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

    expect(screen.getByLabelText('From')).toHaveValue('Warszawa');
    expect(screen.getByLabelText('Distance (km)')).toHaveValue('340');
    expect(screen.getByLabelText('Train')).toBeChecked();
  });
});
