import { useState } from 'react';

import { Button } from '@/components/Button';
import { FormField } from '@/components/FormField';
import { FIELD_LIMITS, hasErrors } from '@/lib/validators';
import { inputClass } from '@/lib/styles';
import type { ComparisonInput } from '@/types/comparison';

import {
  EMPTY_COMPARE_FORM,
  toComparisonInput,
  validateCompare,
  type CompareFormErrors,
  type CompareFormValues,
} from './validation';

interface CompareFormProps {
  isSubmitting?: boolean;
  onSubmit: (input: ComparisonInput) => void;
}

export function CompareForm({ isSubmitting = false, onSubmit }: CompareFormProps) {
  const [values, setValues] = useState(EMPTY_COMPARE_FORM);
  const [errors, setErrors] = useState<CompareFormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  function update<K extends keyof CompareFormValues>(field: K, value: CompareFormValues[K]) {
    const next = { ...values, [field]: value };
    setValues(next);
    if (submitted) setErrors(validateCompare(next));
  }

  function describedBy(field: keyof CompareFormValues) {
    return errors[field] ? `compare-${field}-error` : undefined;
  }

  return (
    <form
      noValidate
      aria-label="Compare form"
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        setSubmitted(true);
        const found = validateCompare(values);
        setErrors(found);
        if (found.distanceKm) setShowAdvanced(true);
        if (!hasErrors(found)) onSubmit(toComparisonInput(values));
      }}
    >
      <FormField label="From" htmlFor="compare-origin" error={errors.origin}>
        <input
          id="compare-origin"
          className={inputClass(Boolean(errors.origin))}
          placeholder="e.g. Warsaw"
          autoComplete="off"
          maxLength={FIELD_LIMITS.placeMaxLength}
          value={values.origin}
          aria-invalid={Boolean(errors.origin)}
          aria-describedby={describedBy('origin')}
          onChange={(event) => update('origin', event.target.value)}
        />
      </FormField>

      <FormField label="To" htmlFor="compare-destination" error={errors.destination}>
        <input
          id="compare-destination"
          className={inputClass(Boolean(errors.destination))}
          placeholder="e.g. Kraków"
          autoComplete="off"
          maxLength={FIELD_LIMITS.placeMaxLength}
          value={values.destination}
          aria-invalid={Boolean(errors.destination)}
          aria-describedby={describedBy('destination')}
          onChange={(event) => update('destination', event.target.value)}
        />
      </FormField>

      <FormField label="Passengers" htmlFor="compare-passengers" error={errors.passengers}>
        <input
          id="compare-passengers"
          type="number"
          min={FIELD_LIMITS.minPassengers}
          max={FIELD_LIMITS.maxPassengers}
          step={1}
          className={inputClass(Boolean(errors.passengers))}
          value={values.passengers}
          aria-invalid={Boolean(errors.passengers)}
          aria-describedby={describedBy('passengers')}
          onChange={(event) => update('passengers', event.target.value)}
        />
      </FormField>

      <div>
        <button
          type="button"
          className="flex items-center gap-1.5 text-sm font-medium text-stone-600 hover:text-stone-900"
          aria-expanded={showAdvanced}
          aria-controls="compare-advanced"
          onClick={() => setShowAdvanced((open) => !open)}
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            fill="currentColor"
            className={`size-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
          >
            <path d="M7.2 4.2a.75.75 0 0 1 1.06 0l5.25 5.27a.75.75 0 0 1 0 1.06L8.26 15.8a.75.75 0 1 1-1.06-1.06L11.92 10 7.2 5.27a.75.75 0 0 1 0-1.06Z" />
          </svg>
          Advanced
        </button>
        {showAdvanced && (
          <div id="compare-advanced" className="mt-3">
            <FormField
              label="Distance (km, optional)"
              htmlFor="compare-distanceKm"
              error={errors.distanceKm}
              hint="Skip the map lookup and use your own road distance."
            >
              <input
                id="compare-distanceKm"
                className={inputClass(Boolean(errors.distanceKm))}
                inputMode="decimal"
                placeholder="e.g. 300"
                value={values.distanceKm}
                aria-invalid={Boolean(errors.distanceKm)}
                aria-describedby={describedBy('distanceKm')}
                onChange={(event) => update('distanceKm', event.target.value)}
              />
            </FormField>
          </div>
        )}
      </div>

      <Button type="submit" isLoading={isSubmitting} className="w-full">
        Compare
      </Button>
    </form>
  );
}
