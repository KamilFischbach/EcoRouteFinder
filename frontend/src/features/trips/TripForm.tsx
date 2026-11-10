import { useState } from 'react';

import { Button } from '@/components/Button';
import { FormField } from '@/components/FormField';
import { cn } from '@/lib/cn';
import { inputClass } from '@/lib/styles';
import { localIsoDate } from '@/lib/validators';
import { MODE_LABELS, TRANSPORT_MODES, type TripInput } from '@/types/trip';

import {
  TRIP_LIMITS,
  emptyTripForm,
  hasErrors,
  toTripInput,
  validateTrip,
  type TripFormErrors,
  type TripFormValues,
} from './validation';

interface TripFormProps {
  initialValues?: TripFormValues;
  submitLabel: string;
  isSubmitting?: boolean;
  serverError?: string | null;
  onSubmit: (input: TripInput) => void;
  onCancel?: () => void;
}

export function TripForm({
  initialValues,
  submitLabel,
  isSubmitting = false,
  serverError,
  onSubmit,
  onCancel,
}: TripFormProps) {
  const [values, setValues] = useState(() => initialValues ?? emptyTripForm());
  const [errors, setErrors] = useState<TripFormErrors>({});
  const [submitted, setSubmitted] = useState(false);

  function update<K extends keyof TripFormValues>(field: K, value: TripFormValues[K]) {
    const next = { ...values, [field]: value };
    setValues(next);
    // Live re-validation only after the first submit attempt, so users aren't nagged while typing.
    if (submitted) setErrors(validateTrip(next));
  }

  function describedBy(field: keyof TripFormValues) {
    return errors[field] ? `trip-${field}-error` : undefined;
  }

  return (
    <form
      noValidate
      aria-label="Trip form"
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        setSubmitted(true);
        const found = validateTrip(values);
        setErrors(found);
        if (!hasErrors(found)) onSubmit(toTripInput(values));
      }}
    >
      <FormField label="From" htmlFor="trip-origin" error={errors.origin}>
        <input
          id="trip-origin"
          className={inputClass(Boolean(errors.origin))}
          placeholder="e.g. Warsaw"
          autoComplete="off"
          maxLength={TRIP_LIMITS.placeMaxLength}
          value={values.origin}
          aria-invalid={Boolean(errors.origin)}
          aria-describedby={describedBy('origin')}
          onChange={(event) => update('origin', event.target.value)}
        />
      </FormField>

      <FormField label="To" htmlFor="trip-destination" error={errors.destination}>
        <input
          id="trip-destination"
          className={inputClass(Boolean(errors.destination))}
          placeholder="e.g. Berlin"
          autoComplete="off"
          maxLength={TRIP_LIMITS.placeMaxLength}
          value={values.destination}
          aria-invalid={Boolean(errors.destination)}
          aria-describedby={describedBy('destination')}
          onChange={(event) => update('destination', event.target.value)}
        />
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Distance (km)" htmlFor="trip-distanceKm" error={errors.distanceKm}>
          <input
            id="trip-distanceKm"
            className={inputClass(Boolean(errors.distanceKm))}
            inputMode="decimal"
            placeholder="e.g. 340"
            value={values.distanceKm}
            aria-invalid={Boolean(errors.distanceKm)}
            aria-describedby={describedBy('distanceKm')}
            onChange={(event) => update('distanceKm', event.target.value)}
          />
        </FormField>
        <FormField label="Passengers" htmlFor="trip-passengers" error={errors.passengers}>
          <input
            id="trip-passengers"
            type="number"
            min={TRIP_LIMITS.minPassengers}
            max={TRIP_LIMITS.maxPassengers}
            step={1}
            className={inputClass(Boolean(errors.passengers))}
            value={values.passengers}
            aria-invalid={Boolean(errors.passengers)}
            aria-describedby={describedBy('passengers')}
            onChange={(event) => update('passengers', event.target.value)}
          />
        </FormField>
      </div>

      <FormField label="Date of travel" htmlFor="trip-travelledOn" error={errors.travelledOn}>
        <input
          id="trip-travelledOn"
          type="date"
          max={localIsoDate()}
          className={inputClass(Boolean(errors.travelledOn))}
          value={values.travelledOn}
          aria-invalid={Boolean(errors.travelledOn)}
          aria-describedby={describedBy('travelledOn')}
          onChange={(event) => update('travelledOn', event.target.value)}
        />
      </FormField>

      <fieldset aria-describedby={describedBy('mode')}>
        <legend className="mb-1.5 text-sm font-medium text-stone-700">Transport mode</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {TRANSPORT_MODES.map((mode) => (
            <label
              key={mode}
              className={cn(
                'flex cursor-pointer items-center justify-center rounded-xl border px-2 py-2 text-center text-sm font-medium transition',
                'border-stone-200 bg-white text-stone-600 hover:border-emerald-300 hover:text-stone-900',
                'has-checked:border-emerald-500 has-checked:bg-emerald-50 has-checked:text-emerald-800',
                'has-focus-visible:ring-4 has-focus-visible:ring-emerald-100',
              )}
            >
              <input
                type="radio"
                name="trip-mode"
                value={mode}
                className="sr-only"
                checked={values.mode === mode}
                onChange={() => update('mode', mode)}
              />
              {MODE_LABELS[mode]}
            </label>
          ))}
        </div>
        {errors.mode && (
          <p id="trip-mode-error" className="mt-1.5 text-sm text-red-600">
            {errors.mode}
          </p>
        )}
      </fieldset>

      <FormField label="Note (optional)" htmlFor="trip-note" error={errors.note}>
        <textarea
          id="trip-note"
          rows={2}
          className={cn(inputClass(Boolean(errors.note)), 'resize-none')}
          placeholder="e.g. business trip"
          value={values.note}
          aria-invalid={Boolean(errors.note)}
          aria-describedby={describedBy('note')}
          onChange={(event) => update('note', event.target.value)}
        />
      </FormField>

      {serverError && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {serverError}
        </p>
      )}

      <div className="flex gap-2 pt-1">
        <Button type="submit" isLoading={isSubmitting} className="flex-1">
          {submitLabel}
        </Button>
        {onCancel && (
          <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
