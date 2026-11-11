import { describe, expect, it } from 'vitest';

import { mcpToolsFixture } from '@/test/handlers';

import {
  errorText,
  initialValues,
  quotedValues,
  toArguments,
  toolFields,
  validateToolForm,
} from './toolForm';

const statsSchema = mcpToolsFixture[0]!.inputSchema;
const emissionsSchema = mcpToolsFixture[1]!.inputSchema;

describe('toolFields', () => {
  it('resolves enums behind $ref and keeps defaults', () => {
    const [range] = toolFields(statsSchema);

    expect(range).toMatchObject({
      name: 'range',
      label: 'Range',
      kind: 'choice',
      options: ['30d', '90d', '12m', 'all'],
      required: false,
      defaultValue: '90d',
    });
  });

  it('reads numbers, integers, limits and required fields', () => {
    const fields = toolFields(emissionsSchema);

    expect(fields.map((f) => [f.name, f.kind, f.required])).toEqual([
      ['distance_km', 'number', true],
      ['mode', 'choice', true],
      ['passengers', 'integer', false],
    ]);
    expect(fields[0]).toMatchObject({ label: 'Distance km', min: 0, max: 40000 });
    expect(initialValues(fields)).toEqual({ distance_km: '', mode: 'car_petrol', passengers: '1' });
  });
});

describe('validation and arguments', () => {
  const fields = toolFields(emissionsSchema);

  it('requires required fields and numbers', () => {
    expect(validateToolForm(fields, { distance_km: '', mode: 'train', passengers: '1.5' })).toEqual(
      { distance_km: 'Required.', passengers: 'Enter a whole number.' },
    );
    expect(validateToolForm(fields, { distance_km: 'abc', mode: 'train', passengers: '' })).toEqual(
      {
        distance_km: 'Enter a number.',
      },
    );
  });

  it('converts numbers (also with a comma) and leaves out empty optional fields', () => {
    expect(toArguments(fields, { distance_km: '12,5', mode: 'train', passengers: '' })).toEqual({
      distance_km: 12.5,
      mode: 'train',
    });
  });
});

describe('result helpers', () => {
  it('reads ready-to-quote strings and tool errors', () => {
    expect(quotedValues({ quote: { co2: '9.4 kg', n: 3 } })).toEqual([['co2', '9.4 kg']]);
    expect(quotedValues({ totals: {} })).toEqual([]);
    expect(errorText({ error: 'Invalid arguments' })).toBe('Invalid arguments');
    expect(errorText(null)).toBeNull();
  });
});
