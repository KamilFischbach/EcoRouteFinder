import { useMutation } from '@tanstack/react-query';
import { useCallback, useReducer, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { tripDraftsApi } from '@/api/tripDrafts';
import { useAdviceMutation, useCompareMutation } from '@/features/compare/useCompare';
import {
  emptyCompareForm,
  fromTripDraft,
  toComparisonInput,
  type CompareFormValues,
} from '@/features/compare/validation';
import type { ComparisonInput } from '@/types/comparison';
import type { DraftField, TripDraft } from '@/types/tripDraft';

import {
  assistantReducer,
  firstMissingField,
  INITIAL_ASSISTANT_STATE,
  type AssistantAction,
  type AssistantMode,
} from './assistantMachine';
import { loadAssistantMode, saveAssistantMode } from './assistantMode';

/** What the compare form should show. A new `key` remounts it with these values. */
export interface FormPrefill {
  key: number;
  values: CompareFormValues;
  focusField?: DraftField | undefined;
  /** Briefly highlight the form so the user notices it was filled in. */
  highlight: boolean;
}

/** EcoAdvisor state for one comparison, for the advisor card. */
export interface AdvisorController {
  isPending: boolean;
  error: Error | null;
  /** Preferences of the latest request for this comparison (pre-fills "Ask again"). */
  preferences: string | undefined;
  ask: (preferences?: string) => void;
}

/**
 * Runs the trip assistant: free text -> draft -> comparison -> EcoAdvisor, using the existing
 * endpoints. Results appear as soon as the comparison is saved; advice follows on its own.
 * Components get state and callbacks from here and never call the API themselves.
 */
export function useTripAssistant() {
  const navigate = useNavigate();
  const draft = useMutation({ mutationFn: (text: string) => tripDraftsApi.create(text) });
  const compare = useCompareMutation();
  const advice = useAdviceMutation();
  const [state, dispatchNow] = useReducer(assistantReducer, INITIAL_ASSISTANT_STATE);
  const [mode, setModeState] = useState(loadAssistantMode);
  const [form, setForm] = useState<FormPrefill>({
    key: 0,
    values: emptyCompareForm(),
    highlight: false,
  });
  // Callbacks of an older run (e.g. slow advice) must not move a newer run's steps.
  const runRef = useRef(0);

  const startRun = useCallback(() => {
    runRef.current += 1;
    const run = runRef.current;
    return (action: AssistantAction) => {
      if (run === runRef.current) dispatchNow(action);
    };
  }, []);

  const setMode = useCallback((next: AssistantMode) => {
    setModeState(next);
    saveAssistantMode(next);
  }, []);

  const runAdvice = useCallback(
    (dispatch: (action: AssistantAction) => void, comparisonId: number, preferences?: string) => {
      dispatch({ type: 'advice_started' });
      advice.mutate(
        { comparisonId, preferences },
        {
          onSuccess: () => dispatch({ type: 'advised' }),
          onError: () => dispatch({ type: 'failed', step: 'advise' }),
        },
      );
    },
    [advice],
  );

  const runCompare = useCallback(
    (dispatch: (action: AssistantAction) => void, input: ComparisonInput, preferences?: string) => {
      dispatch({ type: 'compare_started' });
      compare.mutate(input, {
        onSuccess: (comparison) => {
          dispatch({ type: 'compared' });
          navigate(`/compare/${comparison.id}`);
          runAdvice(dispatch, comparison.id, preferences);
        },
        onError: () => dispatch({ type: 'failed', step: 'compare' }),
      });
    },
    [compare, navigate, runAdvice],
  );

  const applyDraft = useCallback(
    (dispatch: (action: AssistantAction) => void, result: TripDraft, runMode: AssistantMode) => {
      dispatch({ type: 'parsed', draft: result });
      const values = fromTripDraft(result);
      const complete = result.missing_fields.length === 0;
      const goOn = runMode === 'auto' && complete;
      setForm((current) => ({
        key: current.key + 1,
        values,
        focusField: firstMissingField(result.missing_fields),
        highlight: !goOn,
      }));
      if (goOn) runCompare(dispatch, toComparisonInput(values), values.preferences || undefined);
    },
    [runCompare],
  );

  /** "Plan my trip" (auto) or "Fill in the form" (manual). */
  const describe = useCallback(
    (text: string) => {
      const dispatch = startRun();
      const runMode = mode;
      dispatch({ type: 'parse_started', mode: runMode });
      draft.mutate(text, {
        onSuccess: (result) => applyDraft(dispatch, result, runMode),
        onError: () => dispatch({ type: 'failed', step: 'understand' }),
      });
    },
    [applyDraft, draft, mode, startRun],
  );

  /** The compare form's submit; advice starts on its own with the form's preferences. */
  const compareFromForm = useCallback(
    (input: ComparisonInput, preferences?: string) => runCompare(startRun(), input, preferences),
    [runCompare, startRun],
  );

  const advisorFor = useCallback(
    (comparisonId: number): AdvisorController => {
      const current = advice.variables?.comparisonId === comparisonId;
      return {
        isPending: current && advice.isPending,
        error: current && advice.isError ? advice.error : null,
        preferences: current ? advice.variables?.preferences : undefined,
        ask: (preferences) => runAdvice(startRun(), comparisonId, preferences),
      };
    },
    [advice, runAdvice, startRun],
  );

  return {
    state,
    mode,
    setMode,
    describe,
    draftError: draft.error,
    form,
    compareFromForm,
    compare,
    advisorFor,
  };
}

export type TripAssistantController = ReturnType<typeof useTripAssistant>;
