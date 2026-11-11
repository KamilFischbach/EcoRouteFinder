// Turns an MCP tool's JSON schema into form fields and form values into tool arguments.
// The server validates the arguments again (ToolRegistry.run); this only gives quick feedback.
import { parseDecimal } from '@/lib/validators';
import type { JsonSchemaProperty, ToolInputSchema } from '@/types/mcp';

export type FieldKind = 'text' | 'number' | 'integer' | 'choice';

export interface ToolField {
  name: string;
  label: string;
  description: string | null;
  kind: FieldKind;
  options: string[];
  required: boolean;
  defaultValue: string;
  min: number | null;
  max: number | null;
}

export type ToolFormValues = Record<string, string>;
export type ToolFormErrors = Record<string, string>;

/** "distance_km" -> "Distance km" */
function labelFor(name: string): string {
  const words = name.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Follows a local `#/$defs/Name` reference and merges it with the property's own keys. */
function resolve(property: JsonSchemaProperty, schema: ToolInputSchema): JsonSchemaProperty {
  const name = property.$ref?.replace('#/$defs/', '');
  const target = name ? schema.$defs?.[name] : undefined;
  return target ? { ...target, ...property } : property;
}

function kindOf(property: JsonSchemaProperty): FieldKind {
  if (Array.isArray(property.enum)) return 'choice';
  if (property.type === 'integer') return 'integer';
  if (property.type === 'number') return 'number';
  return 'text';
}

export function toolFields(schema: ToolInputSchema): ToolField[] {
  const required = new Set(schema.required ?? []);
  return Object.entries(schema.properties ?? {}).map(([name, raw]) => {
    const property = resolve(raw, schema);
    return {
      name,
      label: labelFor(name),
      description: property.description ?? null,
      kind: kindOf(property),
      options: (property.enum ?? []).map(String),
      required: required.has(name),
      defaultValue: property.default === undefined ? '' : String(property.default),
      min: property.minimum ?? property.exclusiveMinimum ?? null,
      max: property.maximum ?? null,
    };
  });
}

export function initialValues(fields: ToolField[]): ToolFormValues {
  return Object.fromEntries(
    fields.map((field) => [field.name, field.defaultValue || (field.options[0] ?? '')]),
  );
}

function fieldError(field: ToolField, raw: string): string | undefined {
  const value = raw.trim();
  if (!value) return field.required ? 'Required.' : undefined;
  if (field.kind === 'number' || field.kind === 'integer') {
    const number = parseDecimal(value);
    if (!Number.isFinite(number)) return 'Enter a number.';
    if (field.kind === 'integer' && !Number.isInteger(number)) return 'Enter a whole number.';
  }
  return undefined;
}

export function validateToolForm(fields: ToolField[], values: ToolFormValues): ToolFormErrors {
  const errors: ToolFormErrors = {};
  for (const field of fields) {
    const error = fieldError(field, values[field.name] ?? '');
    if (error) errors[field.name] = error;
  }
  return errors;
}

/** Form values -> `tools/call` arguments; empty optional fields are left out. */
export function toArguments(fields: ToolField[], values: ToolFormValues): Record<string, unknown> {
  const args: Record<string, unknown> = {};
  for (const field of fields) {
    const value = (values[field.name] ?? '').trim();
    if (!value) continue;
    const numeric = field.kind === 'number' || field.kind === 'integer';
    args[field.name] = numeric ? parseDecimal(value) : value;
  }
  return args;
}

/** The ready-to-quote strings a tool returns under `quote`, if any. */
export function quotedValues(data: unknown): [string, string][] {
  if (typeof data !== 'object' || data === null || !('quote' in data)) return [];
  const { quote } = data as { quote: unknown };
  if (typeof quote !== 'object' || quote === null) return [];
  return Object.entries(quote).filter(
    (entry): entry is [string, string] => typeof entry[1] === 'string',
  );
}

export function errorText(data: unknown): string | null {
  if (typeof data === 'object' && data !== null && 'error' in data) {
    const { error } = data as { error: unknown };
    return typeof error === 'string' ? error : null;
  }
  return null;
}
