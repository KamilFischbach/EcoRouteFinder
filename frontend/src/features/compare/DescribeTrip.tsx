import { useId, useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { AiIcon } from '@/components/AiIcon';
import { Button } from '@/components/Button';
import { cn } from '@/lib/cn';
import { inputClass } from '@/lib/styles';
import { FIELD_LIMITS } from '@/lib/validators';
import { MODE_LABELS } from '@/types/trip';
import type { DraftField, TripDraft } from '@/types/tripDraft';

import { useTripDraftMutation } from './useTripDraft';

const FIELD_LABELS: Record<DraftField, string> = {
  origin: 'From',
  destination: 'To',
  passengers: 'Passengers',
};

interface DescribeTripProps {
  /** Called with the parsed draft. It fills the form; it never submits it. */
  onDraft: (draft: TripDraft) => void;
}

function DraftSummary({ draft }: { draft: TripDraft }) {
  const byAi = draft.parsed_by === 'llm';
  return (
    <div role="status" className="mt-3 space-y-1.5 text-sm">
      <span
        className={cn(
          'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
          byAi ? 'bg-violet-100 text-violet-800' : 'bg-stone-200 text-stone-700',
        )}
      >
        {byAi ? 'Filled by AI' : 'Filled by rules'}
      </span>
      {draft.missing_fields.length > 0 ? (
        <p className="text-amber-800">
          Not found in your text: {draft.missing_fields.map((f) => FIELD_LABELS[f]).join(', ')}.
          Please fill in below.
        </p>
      ) : (
        <p className="text-stone-600">Check the form below, then press Compare.</p>
      )}
      {draft.mode && <p className="text-stone-600">You mentioned: {MODE_LABELS[draft.mode]}.</p>}
    </div>
  );
}

export function DescribeTrip({ onDraft }: DescribeTripProps) {
  const [text, setText] = useState('');
  const draft = useTripDraftMutation();
  const id = useId();
  const trimmed = text.trim();

  return (
    <form
      aria-label="Trip description"
      className="rounded-xl bg-emerald-50/60 p-4 ring-1 ring-emerald-100"
      onSubmit={(event) => {
        event.preventDefault();
        if (trimmed) draft.mutate(trimmed, { onSuccess: onDraft });
      }}
    >
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-stone-700">
        Describe your trip
      </label>
      <textarea
        id={id}
        rows={2}
        maxLength={FIELD_LIMITS.tripDescriptionMaxLength}
        className={cn(inputClass(), 'resize-none')}
        placeholder="e.g. Tomorrow I'm going from Gdynia to Toruń with my wife"
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-xs text-stone-500">English or Polish</span>
        <Button
          type="submit"
          size="sm"
          variant="secondary"
          isLoading={draft.isPending}
          disabled={!trimmed}
        >
          {!draft.isPending && <AiIcon />}
          Fill in with AI
        </Button>
      </div>
      {draft.isPending && (
        <p className="mt-2 text-xs text-stone-500">
          Reading your trip… the local model may need a few seconds.
        </p>
      )}
      {draft.isError && (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {getErrorMessage(draft.error)}
        </p>
      )}
      {draft.data && !draft.isPending && <DraftSummary draft={draft.data} />}
    </form>
  );
}
