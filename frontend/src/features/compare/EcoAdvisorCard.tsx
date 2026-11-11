import { useId, useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { AiIcon } from '@/components/AiIcon';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import type { AdvisorController } from '@/features/assistant/useTripAssistant';
import { ModeBadge } from '@/features/trips/ModeBadge';
import { cn } from '@/lib/cn';
import { inputClass } from '@/lib/styles';
import { FIELD_LIMITS } from '@/lib/validators';
import type { Advice, Comparison } from '@/types/comparison';

function SourceBadge({ advice }: { advice: Advice }) {
  return advice.used_llm ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800">
      <AiIcon className="size-3" />
      AI · {advice.model}
    </span>
  ) : (
    <span className="rounded-full bg-stone-200 px-2 py-0.5 text-xs font-medium text-stone-700">
      Rule-based (AI offline)
    </span>
  );
}

function ToolTrace({ advice }: { advice: Advice }) {
  return (
    <details className="group mt-4 rounded-xl bg-stone-50 px-4 py-3 text-sm">
      <summary className="cursor-pointer font-medium text-stone-700 select-none">
        How I got this
      </summary>
      <div className="mt-2 space-y-2 text-stone-600">
        <p>
          {advice.used_llm
            ? `Answer written by the local model ${advice.model}. All numbers come from EcoRoute's calculator.`
            : 'The AI model was unavailable or its answer failed our checks, so a rule-based advisor picked the option.'}
        </p>
        {advice.preferences && <p>Your preferences: “{advice.preferences}”</p>}
        {advice.tool_trace.length === 0 ? (
          <p>No extra tools were needed; the advice uses the saved comparison.</p>
        ) : (
          <ol aria-label="Tool calls" className="space-y-1">
            {advice.tool_trace.map((call, index) => (
              <li key={index} className="flex items-start gap-2 font-mono text-xs">
                <span aria-label={call.ok ? 'ok' : 'failed'}>{call.ok ? '✓' : '✗'}</span>
                <span className="break-all">
                  {call.tool}({JSON.stringify(call.arguments)})
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </details>
  );
}

// The weather is used for the advice (e.g. no bike in the rain) but not shown here.
function AdviceView({ advice }: { advice: Advice }) {
  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-stone-600">Recommended:</span>
        <ModeBadge mode={advice.recommended_mode} />
        <SourceBadge advice={advice} />
      </div>
      <p className="mt-3 text-base text-stone-900">{advice.summary}</p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-stone-700">
        {advice.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <ToolTrace advice={advice} />
    </div>
  );
}

function ThinkingSkeleton() {
  return (
    <div className="mt-4" role="status">
      <p className="text-sm text-stone-600">
        EcoAdvisor is thinking… (local model, can take ~20 s)
      </p>
      <div aria-hidden="true" className="mt-3 animate-pulse space-y-2.5">
        <div className="h-5 w-32 rounded-full bg-stone-200" />
        <div className="h-4 w-full rounded bg-stone-100" />
        <div className="h-4 w-5/6 rounded bg-stone-100" />
        <div className="h-4 w-2/3 rounded bg-stone-100" />
      </div>
    </div>
  );
}

interface EcoAdvisorCardProps {
  comparison: Comparison;
  advisor: AdvisorController;
}

export function EcoAdvisorCard({ comparison, advisor }: EcoAdvisorCardProps) {
  const advice = comparison.advice;
  // What the user typed, tied to the advice it was typed for: a new answer empties the box.
  // Before the first answer it starts from the preferences parsed from the trip description.
  const [draft, setDraft] = useState<{ text: string; advice: Advice | null } | null>(null);
  const typed = draft && draft.advice === advice ? draft.text : null;
  const preferences = typed ?? (advice ? '' : (advisor.preferences ?? ''));
  const inputId = useId();
  const ask = () => advisor.ask(preferences.trim() || undefined);

  return (
    <Card
      aria-label="EcoAdvisor"
      className={cn('px-5 py-5 sm:px-6', (advice || advisor.isPending) && 'ring-2 ring-violet-100')}
    >
      <div className="flex items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-lg bg-violet-50 ring-1 ring-violet-100">
          <AiIcon />
        </span>
        <div>
          <h2 className="font-semibold text-stone-900">EcoAdvisor</h2>
          <p className="text-xs text-stone-500">Personal advice based on this comparison</p>
        </div>
      </div>

      {advisor.isPending && <ThinkingSkeleton />}
      {advisor.error && !advisor.isPending && (
        <div className="mt-4 flex flex-col gap-2 rounded-xl bg-red-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <p role="alert" className="text-sm text-red-700">
            EcoAdvisor couldn't answer: {getErrorMessage(advisor.error)} The comparison below is
            still valid.
          </p>
          <Button variant="secondary" size="sm" onClick={ask}>
            Try again
          </Button>
        </div>
      )}
      {advice && !advisor.isPending && <AdviceView advice={advice} />}

      <form
        className="mt-4 flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          ask();
        }}
      >
        <label htmlFor={inputId} className="sr-only">
          Your preferences (optional)
        </label>
        <input
          id={inputId}
          className={cn(inputClass(), 'sm:flex-1')}
          placeholder="e.g. “I have skis”, “cheapest please”, “I want to be there fast”"
          maxLength={FIELD_LIMITS.preferencesMaxLength}
          value={preferences}
          onChange={(event) => setDraft({ text: event.target.value, advice })}
        />
        <Button
          type="submit"
          variant={advice ? 'secondary' : 'primary'}
          isLoading={advisor.isPending}
        >
          {!advisor.isPending && <AiIcon className={advice ? undefined : 'invert'} />}
          {advice ? 'Ask again' : 'Ask EcoAdvisor'}
        </Button>
      </form>
    </Card>
  );
}
