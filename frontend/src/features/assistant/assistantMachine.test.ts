import { describe, expect, it } from 'vitest';

import type { TripDraft } from '@/types/tripDraft';

import {
  assistantReducer,
  firstMissingField,
  INITIAL_ASSISTANT_STATE,
  missingMessage,
  stepStatuses,
  type AssistantAction,
  type AssistantState,
} from './assistantMachine';

const COMPLETE: TripDraft = {
  origin: 'Tczew',
  destination: 'Karpacz',
  passengers: 2,
  mode: null,
  preferences: 'ski equipment, comfort matters',
  missing_fields: [],
  parsed_by: 'llm',
};
const NO_DESTINATION: TripDraft = {
  ...COMPLETE,
  destination: null,
  missing_fields: ['destination'],
  parsed_by: 'rules',
};

function run(...actions: AssistantAction[]): AssistantState {
  return actions.reduce(assistantReducer, INITIAL_ASSISTANT_STATE);
}

describe('assistantReducer', () => {
  it('goes through every step in auto mode', () => {
    const parsing = run({ type: 'parse_started', mode: 'auto' });
    expect(stepStatuses(parsing)).toEqual({
      understand: 'active',
      compare: 'waiting',
      advise: 'waiting',
    });

    const comparing = assistantReducer(parsing, { type: 'parsed', draft: COMPLETE });
    expect(comparing.phase).toBe('comparing');
    expect(comparing.parsedBy).toBe('llm');

    const advising = run(
      { type: 'parse_started', mode: 'auto' },
      { type: 'parsed', draft: COMPLETE },
      { type: 'compare_started' },
      { type: 'compared' },
    );
    expect(stepStatuses(advising)).toEqual({
      understand: 'done',
      compare: 'done',
      advise: 'active',
    });

    const done = assistantReducer(advising, { type: 'advised' });
    expect(done.phase).toBe('done');
    expect(stepStatuses(done)).toEqual({ understand: 'done', compare: 'done', advise: 'done' });
  });

  it('stops for input when auto mode misses a field', () => {
    const state = run(
      { type: 'parse_started', mode: 'auto' },
      { type: 'parsed', draft: NO_DESTINATION },
    );

    expect(state.phase).toBe('needs_input');
    expect(state.missing).toEqual(['destination']);
    expect(stepStatuses(state)).toEqual({
      understand: 'done',
      compare: 'waiting',
      advise: 'waiting',
    });
  });

  it('only fills the form in manual mode, even with every field found', () => {
    const state = run(
      { type: 'parse_started', mode: 'manual' },
      { type: 'parsed', draft: COMPLETE },
    );

    expect(state.phase).toBe('needs_input');
    expect(state.missing).toEqual([]);
  });

  it('keeps the parse step when the filled form is submitted', () => {
    const state = run(
      { type: 'parse_started', mode: 'manual' },
      { type: 'parsed', draft: COMPLETE },
      { type: 'compare_started' },
    );

    expect(state.parsedBy).toBe('llm');
    expect(stepStatuses(state).understand).toBe('done');
    expect(stepStatuses(state).compare).toBe('active');
  });

  it('marks the parse step skipped for a plain form comparison', () => {
    const state = run({ type: 'compare_started' }, { type: 'compared' });

    expect(stepStatuses(state)).toEqual({
      understand: 'skipped',
      compare: 'done',
      advise: 'active',
    });
  });

  it('does not reuse an old parse for a later form comparison', () => {
    const state = run(
      { type: 'parse_started', mode: 'auto' },
      { type: 'parsed', draft: COMPLETE },
      { type: 'compare_started' },
      { type: 'compared' },
      { type: 'advised' },
      { type: 'compare_started' },
    );

    expect(state.parsedBy).toBeNull();
    expect(stepStatuses(state).understand).toBe('skipped');
  });

  it('marks the failed step and keeps earlier ones done', () => {
    const adviceFailed = run(
      { type: 'compare_started' },
      { type: 'compared' },
      { type: 'failed', step: 'advise' },
    );
    expect(stepStatuses(adviceFailed)).toEqual({
      understand: 'skipped',
      compare: 'done',
      advise: 'error',
    });

    const parseFailed = run(
      { type: 'parse_started', mode: 'auto' },
      { type: 'failed', step: 'understand' },
    );
    expect(stepStatuses(parseFailed)).toEqual({
      understand: 'error',
      compare: 'waiting',
      advise: 'waiting',
    });
  });

  it('goes back to advising when advice is asked again', () => {
    const state = run(
      { type: 'compare_started' },
      { type: 'compared' },
      { type: 'failed', step: 'advise' },
      { type: 'advice_started' },
    );

    expect(state.phase).toBe('advising');
    expect(state.failedStep).toBeNull();
  });

  it('starts every run from scratch', () => {
    const state = run(
      { type: 'compare_started' },
      { type: 'failed', step: 'compare' },
      { type: 'parse_started', mode: 'manual' },
    );

    expect(state).toEqual({ ...INITIAL_ASSISTANT_STATE, phase: 'parsing', mode: 'manual' });
  });
});

describe('missingMessage', () => {
  it('names the missing fields', () => {
    expect(missingMessage(['destination'])).toBe(
      "I couldn't find the destination — fill it in and press Compare.",
    );
    expect(missingMessage(['origin', 'destination', 'passengers'])).toBe(
      "I couldn't find the starting point, the destination and how many of you are travelling — fill them in and press Compare.",
    );
  });

  it('asks to check the form when nothing is missing', () => {
    expect(missingMessage([])).toBe('The form is filled in. Check it, then press Compare.');
  });
});

describe('firstMissingField', () => {
  it('follows the form order', () => {
    expect(firstMissingField(['passengers', 'destination'])).toBe('destination');
    expect(firstMissingField([])).toBeUndefined();
  });
});
