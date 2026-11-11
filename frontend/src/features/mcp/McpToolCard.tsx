import { useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { FormField } from '@/components/FormField';
import { inputClass } from '@/lib/styles';
import type { McpCallResult, McpTool } from '@/types/mcp';

import { McpBadge } from './McpBadge';
import {
  errorText,
  initialValues,
  quotedValues,
  toArguments,
  toolFields,
  validateToolForm,
  type ToolField,
  type ToolFormErrors,
} from './toolForm';
import { useCallMcpTool } from './useMcp';

interface FieldInputProps {
  id: string;
  field: ToolField;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}

function FieldInput({ id, field, value, error, onChange }: FieldInputProps) {
  const common = {
    id,
    value,
    className: inputClass(Boolean(error)),
    'aria-invalid': Boolean(error),
    'aria-describedby': error ? `${id}-error` : undefined,
  };
  if (field.kind === 'choice') {
    return (
      <select {...common} onChange={(event) => onChange(event.target.value)}>
        {field.options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }
  const numeric = field.kind !== 'text';
  return (
    <input
      {...common}
      inputMode={numeric ? 'decimal' : undefined}
      autoComplete="off"
      placeholder={field.description ?? undefined}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

function ToolResult({ request, result }: { request: string; result: McpCallResult }) {
  const quotes = quotedValues(result.data);
  const error = result.isError ? (errorText(result.data) ?? result.text) : null;
  return (
    <div className="mt-4 space-y-3 border-t border-stone-100 pt-4">
      <div>
        <p className="text-xs font-medium tracking-wide text-stone-500 uppercase">MCP request</p>
        <pre className="mt-1 overflow-x-auto rounded-lg bg-stone-900 px-3 py-2 text-xs text-stone-100">
          {request}
        </pre>
      </div>
      {error ? (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          Tool error (isError: true): {error}
        </p>
      ) : (
        quotes.length > 0 && (
          <dl
            aria-label="Ready-to-quote values"
            className="grid grid-cols-1 gap-x-4 gap-y-1 text-sm sm:grid-cols-2"
          >
            {quotes.map(([key, value]) => (
              <div key={key} className="flex justify-between gap-3 border-b border-stone-100 py-1">
                <dt className="text-stone-500">{key.replace(/_/g, ' ')}</dt>
                <dd className="font-medium text-stone-900 tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
        )
      )}
      <details className="text-sm">
        <summary className="cursor-pointer text-stone-600 hover:text-stone-900">
          MCP response (structuredContent)
        </summary>
        <pre className="mt-2 max-h-80 overflow-auto rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-700">
          {JSON.stringify(result.data, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export function McpToolCard({ tool }: { tool: McpTool }) {
  const fields = toolFields(tool.inputSchema);
  const [values, setValues] = useState(() => initialValues(fields));
  const [errors, setErrors] = useState<ToolFormErrors>({});
  const call = useCallMcpTool();
  const headingId = `mcp-tool-${tool.name}`;

  function run() {
    const found = validateToolForm(fields, values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    call.mutate({ name: tool.name, args: toArguments(fields, values) });
  }

  return (
    <Card aria-labelledby={headingId} className="p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id={headingId} className="font-mono text-base font-semibold text-stone-900">
          {tool.name}
        </h2>
        <McpBadge />
      </div>
      <p className="mt-1 text-sm text-stone-600">{tool.description}</p>

      <form
        noValidate
        aria-label={`Arguments for ${tool.name}`}
        className="mt-4 grid gap-3 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          run();
        }}
      >
        {fields.map((field) => {
          const id = `${headingId}-${field.name}`;
          return (
            <FormField
              key={field.name}
              label={field.required ? field.label : `${field.label} (optional)`}
              htmlFor={id}
              error={errors[field.name]}
            >
              <FieldInput
                id={id}
                field={field}
                value={values[field.name] ?? ''}
                error={errors[field.name]}
                onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))}
              />
            </FormField>
          );
        })}
        <div className="sm:col-span-2">
          <Button type="submit" isLoading={call.isPending} aria-label={`Run ${tool.name}`}>
            Run tool
          </Button>
        </div>
      </form>

      {call.isError && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {getErrorMessage(call.error)}
        </p>
      )}
      {call.data && call.variables && (
        <ToolResult
          request={JSON.stringify(
            {
              method: 'tools/call',
              params: { name: call.variables.name, arguments: call.variables.args },
            },
            null,
            2,
          )}
          result={call.data}
        />
      )}
    </Card>
  );
}
