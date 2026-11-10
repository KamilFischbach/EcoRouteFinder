// Trip assistant state machine: idle -> parsing -> comparing -> advising -> done,
// with needs_input (waiting for the user to press Compare) and error as other stops.
// Pure, so the flow can be tested without React; useTripAssistant runs the side effects.
import type { DraftField, TripDraft } from '@/types/tripDraft';

export type AssistantMode = 'auto' | 'manual';
export type Phase =
  'idle' | 'parsing' | 'comparing' | 'advising' | 'done' | 'needs_input' | 'error';
export type StepId = 'understand' | 'compare' | 'advise';
export type StepStatus = 'waiting' | 'active' | 'done' | 'skipped' | 'error';

export interface AssistantState {
  phase: Phase;
  /** Mode the current run started in (switching modes mid-run doesn't change it). */
  mode: AssistantMode;
  /** Who parsed the text, or null when the run started from the form. */
  parsedBy: TripDraft['parsed_by'] | null;
  missing: DraftField[];
  failedStep: StepId | null;
}

export type AssistantAction =
  | { type: 'parse_started'; mode: AssistantMode }
  | { type: 'parsed'; draft: TripDraft }
  | { type: 'compare_started' }
  | { type: 'compared' }
  | { type: 'advice_started' }
  | { type: 'advised' }
  | { type: 'failed'; step: StepId };

export const INITIAL_ASSISTANT_STATE: AssistantState = {
  phase: 'idle',
  mode: 'auto',
  parsedBy: null,
  missing: [],
  failedStep: null,
};

export function assistantReducer(state: AssistantState, action: AssistantAction): AssistantState {
  switch (action.type) {
    case 'parse_started':
      return { ...INITIAL_ASSISTANT_STATE, phase: 'parsing', mode: action.mode };
    case 'parsed': {
      const missing = action.draft.missing_fields;
      const goOn = state.mode === 'auto' && missing.length === 0;
      return {
        ...state,
        phase: goOn ? 'comparing' : 'needs_input',
        parsedBy: action.draft.parsed_by,
        missing,
      };
    }
    case 'compare_started':
      // From the form: keep a parse that filled it (needs_input), otherwise there was none.
      return {
        ...state,
        phase: 'comparing',
        parsedBy:
          state.phase === 'needs_input' || state.phase === 'comparing' ? state.parsedBy : null,
        missing: [],
        failedStep: null,
      };
    case 'compared':
    case 'advice_started':
      return { ...state, phase: 'advising', failedStep: null };
    case 'advised':
      return { ...state, phase: 'done' };
    case 'failed':
      return { ...state, phase: 'error', failedStep: action.step };
  }
}

const ORDER: StepId[] = ['understand', 'compare', 'advise'];
const ACTIVE_STEP: Partial<Record<Phase, StepId>> = {
  parsing: 'understand',
  comparing: 'compare',
  advising: 'advise',
};

/** Status of each progress step, derived from the state. */
export function stepStatuses(state: AssistantState): Record<StepId, StepStatus> {
  const current: StepId | undefined =
    state.phase === 'error' ? (state.failedStep ?? undefined) : ACTIVE_STEP[state.phase];
  const reached = current === undefined ? -1 : ORDER.indexOf(current);
  const result = {} as Record<StepId, StepStatus>;
  ORDER.forEach((step, index) => {
    if (state.phase === 'idle') result[step] = 'waiting';
    else if (state.phase === 'done') result[step] = 'done';
    else if (state.phase === 'needs_input')
      result[step] = step === 'understand' ? 'done' : 'waiting';
    else if (index < reached) result[step] = 'done';
    else if (index === reached) result[step] = state.phase === 'error' ? 'error' : 'active';
    else result[step] = 'waiting';
  });
  if (state.parsedBy === null && state.phase !== 'idle' && state.phase !== 'parsing') {
    if (state.failedStep !== 'understand') result.understand = 'skipped';
  }
  return result;
}

const MISSING_NAMES: Record<DraftField, string> = {
  origin: 'the starting point',
  destination: 'the destination',
  passengers: 'how many of you are travelling',
};

/** "I couldn't find the destination — fill it in and press Compare." */
export function missingMessage(missing: DraftField[]): string {
  if (missing.length === 0) return 'The form is filled in. Check it, then press Compare.';
  const names = missing.map((field) => MISSING_NAMES[field]);
  const list =
    names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`;
  const pronoun = names.length === 1 ? 'it' : 'them';
  return `I couldn't find ${list} — fill ${pronoun} in and press Compare.`;
}

/** The field to focus first: the earliest missing one in form order. */
export function firstMissingField(missing: DraftField[]): DraftField | undefined {
  return (['origin', 'destination', 'passengers'] as const).find((f) => missing.includes(f));
}

export function isBusy(state: AssistantState): boolean {
  return state.phase === 'parsing' || state.phase === 'comparing' || state.phase === 'advising';
}
