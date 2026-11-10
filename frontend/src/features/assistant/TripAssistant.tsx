import { useId, useRef, useState, type KeyboardEvent } from 'react';

import { getErrorMessage } from '@/api/errors';
import { AiIcon } from '@/components/AiIcon';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Spinner } from '@/components/Spinner';
import { cn } from '@/lib/cn';
import { inputClass } from '@/lib/styles';
import { FIELD_LIMITS } from '@/lib/validators';

import {
  missingMessage,
  stepStatuses,
  type AssistantMode,
  type AssistantState,
  type StepId,
  type StepStatus,
} from './assistantMachine';

const EXAMPLES = [
  {
    label: 'Ski trip Tczew → Karpacz for 2 with equipment',
    text: 'Ski trip Tczew → Karpacz for 2 with equipment',
  },
  {
    label: 'Cheapest way from Gdańsk to Kraków, solo',
    text: 'Cheapest way from Gdańsk to Kraków, solo',
  },
  {
    label: 'Weekend in Warsaw from Gdynia, 4 friends, fast',
    text: 'Weekend in Warsaw from Gdynia, 4 friends, fast',
  },
];

const MODES: { value: AssistantMode; label: string; description: string; action: string }[] = [
  {
    value: 'auto',
    label: 'Auto',
    description: 'Reads your trip, compares all options and asks EcoAdvisor in one go.',
    action: 'Plan my trip',
  },
  {
    value: 'manual',
    label: 'Manual',
    description: 'Only fills in the form below, so you can check it before pressing Compare.',
    action: 'Fill in the form',
  },
];

const STEP_LABELS: Record<StepId, string> = {
  understand: 'Understanding your trip',
  compare: 'Comparing 6 ways to travel',
  advise: 'Asking EcoAdvisor',
};

const STATUS_TEXT: Record<StepStatus, string> = {
  waiting: 'waiting',
  active: 'in progress',
  done: 'done',
  skipped: 'skipped',
  error: 'failed',
};

interface TripAssistantProps {
  state: AssistantState;
  mode: AssistantMode;
  onModeChange: (mode: AssistantMode) => void;
  onSubmit: (text: string) => void;
  /** Error of the parse request, shown when the first step failed. */
  draftError: Error | null;
}

function ModeSwitch({
  mode,
  onChange,
}: {
  mode: AssistantMode;
  onChange: (mode: AssistantMode) => void;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent, index: number) {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const next = MODES[(index + 1) % MODES.length];
    if (!next) return;
    onChange(next.value);
    refs.current[MODES.indexOf(next)]?.focus();
  }

  return (
    <div
      role="radiogroup"
      aria-label="Assistant mode"
      className="inline-flex rounded-xl bg-stone-100 p-1"
    >
      {MODES.map((option, index) => {
        const checked = option.value === mode;
        return (
          <button
            key={option.value}
            ref={(element) => {
              refs.current[index] = element;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            className={cn(
              'h-8 rounded-lg px-4 text-sm font-medium transition-colors',
              'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600',
              checked ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-600 hover:text-stone-900',
            )}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function StepIcon({ status, index }: { status: StepStatus; index: number }) {
  const base =
    'flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold';
  if (status === 'active') {
    return (
      <span className={cn(base, 'text-emerald-600')}>
        <Spinner size="sm" />
      </span>
    );
  }
  if (status === 'done') {
    return (
      <span className={cn(base, 'bg-emerald-600 text-white')} aria-hidden="true">
        ✓
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className={cn(base, 'bg-red-100 text-red-700')} aria-hidden="true">
        !
      </span>
    );
  }
  return (
    <span
      className={cn(base, 'bg-stone-100 text-stone-500', status === 'skipped' && 'line-through')}
      aria-hidden="true"
    >
      {status === 'skipped' ? '–' : index + 1}
    </span>
  );
}

function ParsedByBadge({ parsedBy }: { parsedBy: AssistantState['parsedBy'] }) {
  if (parsedBy === null) return null;
  return parsedBy === 'llm' ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800">
      <AiIcon className="size-3" />
      AI
    </span>
  ) : (
    <span className="rounded-full bg-stone-200 px-2 py-0.5 text-xs font-medium text-stone-700">
      rules
    </span>
  );
}

function StepProgress({ state }: { state: AssistantState }) {
  const statuses = stepStatuses(state);
  return (
    <ol aria-label="Progress" className="flex flex-col gap-2 sm:flex-row sm:gap-6">
      {(Object.keys(STEP_LABELS) as StepId[]).map((step, index) => {
        const status = statuses[step];
        return (
          <li
            key={step}
            aria-label={`${STEP_LABELS[step]}: ${STATUS_TEXT[status]}`}
            data-status={status}
            className="flex items-center gap-2 text-sm"
          >
            <StepIcon status={status} index={index} />
            <span
              className={cn(
                status === 'waiting' || status === 'skipped' ? 'text-stone-500' : 'text-stone-800',
                status === 'active' && 'font-medium',
                status === 'error' && 'text-red-700',
              )}
            >
              {STEP_LABELS[step]}
              {status === 'skipped' && <span className="text-stone-400"> (skipped)</span>}
            </span>
            {step === 'understand' && status === 'done' && (
              <ParsedByBadge parsedBy={state.parsedBy} />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function StatusMessage({ state, draftError }: { state: AssistantState; draftError: Error | null }) {
  if (state.phase === 'needs_input') {
    return (
      <p role="status" className="text-sm text-amber-800">
        {missingMessage(state.missing)}
      </p>
    );
  }
  if (state.phase === 'error' && state.failedStep === 'understand') {
    return (
      <p role="alert" className="text-sm text-red-600">
        {getErrorMessage(draftError)}
      </p>
    );
  }
  if (state.phase === 'error' && state.failedStep === 'compare') {
    return <p className="text-sm text-red-600">The comparison failed. See the details below.</p>;
  }
  return null;
}

export function TripAssistant({
  state,
  mode,
  onModeChange,
  onSubmit,
  draftError,
}: TripAssistantProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const id = useId();
  const trimmed = text.trim();
  const working = state.phase === 'parsing' || state.phase === 'comparing';
  const current = MODES.find((option) => option.value === mode) ?? MODES[0];
  const max = FIELD_LIMITS.tripDescriptionMaxLength;

  function submit() {
    if (trimmed && !working) onSubmit(trimmed);
  }

  return (
    <Card aria-label="Trip assistant" className="px-5 py-5 sm:px-6">
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-violet-50 ring-1 ring-violet-100">
            <AiIcon />
          </span>
          <div>
            <h2 className="font-semibold text-stone-900">Trip assistant</h2>
            <p className="text-xs text-stone-500">
              Describe your trip in English or Polish, the way you would tell a friend.
            </p>
          </div>
        </div>

        <div>
          <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-stone-700">
            Describe your trip
          </label>
          <textarea
            ref={textareaRef}
            id={id}
            rows={3}
            maxLength={max}
            aria-describedby={`${id}-count`}
            className={cn(inputClass(), 'resize-y text-base sm:text-sm')}
            placeholder="e.g. I want to go skiing with my girlfriend from Tczew to Karpacz. We have ski equipment and comfort matters to us."
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                submit();
              }
            }}
          />
          <div className="mt-1 flex justify-between gap-2 text-xs text-stone-500">
            <span>Ctrl/⌘ + Enter to send</span>
            <span id={`${id}-count`}>
              {text.length}/{max} characters
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-stone-500">Try:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example.label}
              type="button"
              className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 ring-1 ring-emerald-100 hover:bg-emerald-100 focus-visible:outline-2 focus-visible:outline-emerald-600"
              onClick={() => {
                setText(example.text);
                textareaRef.current?.focus();
              }}
            >
              {example.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <ModeSwitch mode={mode} onChange={onModeChange} />
            <p className="text-xs text-stone-500">{current?.description}</p>
          </div>
          <Button
            type="submit"
            isLoading={working}
            disabled={!trimmed}
            className="w-full sm:w-auto"
          >
            {!working && <AiIcon className="invert" />}
            {current?.action}
          </Button>
        </div>

        {state.phase !== 'idle' && (
          <div className="space-y-2 border-t border-stone-100 pt-4" aria-live="polite">
            <StepProgress state={state} />
            <StatusMessage state={state} draftError={draftError} />
          </div>
        )}
      </form>
    </Card>
  );
}
