import { afterEach, describe, expect, it, vi } from 'vitest';

import { ASSISTANT_MODE_KEY, loadAssistantMode, saveAssistantMode } from './assistantMode';

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe('assistant mode storage', () => {
  it('defaults to auto', () => {
    expect(loadAssistantMode()).toBe('auto');
  });

  it('remembers the saved mode', () => {
    saveAssistantMode('manual');

    expect(window.localStorage.getItem(ASSISTANT_MODE_KEY)).toBe('manual');
    expect(loadAssistantMode()).toBe('manual');
  });

  it('ignores unknown stored values', () => {
    window.localStorage.setItem(ASSISTANT_MODE_KEY, 'turbo');

    expect(loadAssistantMode()).toBe('auto');
  });

  it('never throws when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });

    expect(() => saveAssistantMode('manual')).not.toThrow();
    expect(loadAssistantMode()).toBe('auto');
  });
});
