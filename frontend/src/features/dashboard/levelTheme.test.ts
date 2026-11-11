import { describe, expect, it } from 'vitest';

import { levelTheme } from './levelTheme';

describe('levelTheme', () => {
  it('gives every level its own icon and gradient', () => {
    const names = ['Seedling', 'Sprout', 'Sapling', 'Tree', 'Forest'];
    const themes = names.map(levelTheme);

    expect(themes.map((t) => t.icon)).toEqual(['seedling', 'sprout', 'sapling', 'tree', 'forest']);
    expect(new Set(themes.map((t) => t.gradient)).size).toBe(names.length);
  });

  it('falls back to the first level for an unknown name', () => {
    expect(levelTheme('Galaxy')).toEqual(levelTheme('Seedling'));
  });
});
