import type { AssistantMode } from './assistantMachine';

export const ASSISTANT_MODE_KEY = 'ecoroute.assistantMode';
export const DEFAULT_ASSISTANT_MODE: AssistantMode = 'auto';

/** Remembered mode. Storage can be missing or blocked (private mode), so this never throws. */
export function loadAssistantMode(): AssistantMode {
  try {
    const stored = window.localStorage.getItem(ASSISTANT_MODE_KEY);
    return stored === 'auto' || stored === 'manual' ? stored : DEFAULT_ASSISTANT_MODE;
  } catch {
    return DEFAULT_ASSISTANT_MODE;
  }
}

export function saveAssistantMode(mode: AssistantMode): void {
  try {
    window.localStorage.setItem(ASSISTANT_MODE_KEY, mode);
  } catch {
    // Not remembered this time; the switch still works for this visit.
  }
}
