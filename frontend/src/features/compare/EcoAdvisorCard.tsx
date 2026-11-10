import { useId, useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { AiIcon } from '@/components/AiIcon';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Spinner } from '@/components/Spinner';
import { ModeBadge } from '@/features/trips/ModeBadge';
import { cn } from '@/lib/cn';
import { inputClass } from '@/lib/styles';
import { FIELD_LIMITS } from '@/lib/validators';
import type { Advice, Comparison } from '@/types/comparison';

import { useAdviceMutation } from './useCompare';
import { WeatherIcon } from './WeatherIcon';

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
            : 'The AI model was unavailable or its answer failed our checks, so a rule-based advisor picked the greenest practical option.'}
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

function AdviceView({ advice }: { advice: Advice }) {
  const weather = advice.weather;
  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-stone-600">Recommended:</span>
        <ModeBadge mode={advice.recommended_mode} />
        <SourceBadge advice={advice} />
      </div>
      <p className="mt-3 text-stone-900">{advice.summary}</p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-stone-700">
        {advice.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      {weather && (
        <p className="mt-3 flex items-center gap-2 text-sm text-stone-600">
          <WeatherIcon code={weather.weather_code} className="size-5 text-sky-600" />
          {weather.location}: {Math.round(weather.temperature_c)} °C
          {weather.description ? `, ${weather.description}` : ''}, wind{' '}
          {Math.round(weather.wind_kph)} km/h
        </p>
      )}
      <ToolTrace advice={advice} />
    </div>
  );
}

export function EcoAdvisorCard({ comparison }: { comparison: Comparison }) {
  const [preferences, setPreferences] = useState('');
  const advise = useAdviceMutation(comparison.id);
  const inputId = useId();
  const advice = comparison.advice;

  return (
    <Card aria-label="EcoAdvisor" className="px-5 py-5 sm:px-6">
      <div className="flex items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-lg bg-violet-50 ring-1 ring-violet-100">
          <AiIcon />
        </span>
        <div>
          <h2 className="font-semibold text-stone-900">EcoAdvisor</h2>
          <p className="text-xs text-stone-500">Personal advice based on this comparison</p>
        </div>
      </div>

      <form
        className="mt-4 flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          advise.mutate(preferences.trim() || undefined);
        }}
      >
        <label htmlFor={inputId} className="sr-only">
          Your preferences (optional)
        </label>
        <input
          id={inputId}
          className={cn(inputClass(), 'sm:flex-1')}
          placeholder="Optional: “I have luggage”, “cheapest please”"
          maxLength={FIELD_LIMITS.preferencesMaxLength}
          value={preferences}
          onChange={(event) => setPreferences(event.target.value)}
        />
        <Button type="submit" isLoading={advise.isPending}>
          {!advise.isPending && <AiIcon className="invert" />}
          {advice ? 'Ask again' : 'Ask EcoAdvisor'}
        </Button>
      </form>

      {advise.isPending && (
        <div role="status" className="mt-4 flex items-center gap-2 text-sm text-stone-600">
          <Spinner size="sm" />
          EcoAdvisor is thinking… a local model can take 10–20 seconds.
        </div>
      )}
      {advise.isError && !advise.isPending && (
        <p role="alert" className="mt-4 text-sm text-red-600">
          {getErrorMessage(advise.error)}
        </p>
      )}
      {advice && !advise.isPending && <AdviceView advice={advice} />}
    </Card>
  );
}
