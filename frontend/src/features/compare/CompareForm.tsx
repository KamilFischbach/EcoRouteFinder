import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/Button';
import { FormField } from '@/components/FormField';
import { cn } from '@/lib/cn';
import { FIELD_LIMITS, hasErrors, latestTravelDate } from '@/lib/validators';
import { inputClass } from '@/lib/styles';
import type { ComparisonInput } from '@/types/comparison';

import {
  emptyCompareForm,
  toComparisonInput,
  toPreferences,
  validateCompare,
  type CompareFormErrors,
  type CompareFormValues,
} from './validation';

type FocusableField = 'origin' | 'destination' | 'passengers';

interface CompareFormProps {
  /** Pre-fill (e.g. from the trip assistant). Change the component `key` to apply new values. */
  initialValues?: CompareFormValues;
  /** Focus this field on mount, e.g. the first one the assistant couldn't find. */
  focusField?: FocusableField | undefined;
  /** Play a short highlight on mount so the user notices the form was filled in. */
  highlight?: boolean;
  isSubmitting?: boolean;
  onSubmit: (input: ComparisonInput, preferences: string | undefined) => void;
}

export function CompareForm({
  initialValues,
  focusField,
  highlight = false,
  isSubmitting = false,
  onSubmit,
}: CompareFormProps) {
  const [values, setValues] = useState(() => initialValues ?? emptyCompareForm());
  const [errors, setErrors] = useState<CompareFormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (focusField) formRef.current?.querySelector<HTMLElement>(`#compare-${focusField}`)?.focus();
  }, [focusField]);

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
      ref={formRef}
      noValidate
      aria-label="Compare form"
      className={cn('space-y-5 rounded-xl', highlight && 'animate-form-filled')}
      onSubmit={(event) => {
        event.preventDefault();
        setSubmitted(true);
        const found = validateCompare(values);
        setErrors(found);
        if (found.distanceKm) setShowAdvanced(true);
        if (!hasErrors(found)) onSubmit(toComparisonInput(values), toPreferences(values));
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

      <div className="grid grid-cols-2 gap-4">
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
        <FormField label="Date of travel" htmlFor="compare-travelledOn" error={errors.travelledOn}>
          <input
            id="compare-travelledOn"
            type="date"
            max={latestTravelDate()}
            className={inputClass(Boolean(errors.travelledOn))}
            value={values.travelledOn}
            aria-invalid={Boolean(errors.travelledOn)}
            aria-describedby={describedBy('travelledOn')}
            onChange={(event) => update('travelledOn', event.target.value)}
          />
        </FormField>
      </div>

      <FormField
        label="What matters to you?"
        htmlFor="compare-preferences"
        error={errors.preferences}
        hint="Optional. EcoAdvisor takes it into account, e.g. “skis and comfort”, “cheapest”."
      >
        <textarea
          id="compare-preferences"
          rows={2}
          className={cn(inputClass(Boolean(errors.preferences)), 'resize-none')}
          placeholder="e.g. We have ski equipment and comfort matters"
          maxLength={FIELD_LIMITS.preferencesMaxLength}
          value={values.preferences}
          aria-invalid={Boolean(errors.preferences)}
          aria-describedby={describedBy('preferences')}
          onChange={(event) => update('preferences', event.target.value)}
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
