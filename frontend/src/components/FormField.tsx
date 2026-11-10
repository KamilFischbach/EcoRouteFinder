import type { ReactNode } from 'react';

interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string | undefined;
  hint?: string;
  children: ReactNode;
}

/** Label + control + error message. The control should set `aria-describedby={errorId(htmlFor)}`. */
export function FormField({ label, htmlFor, error, hint, children }: FormFieldProps) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium text-stone-700">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${htmlFor}-error`} className="mt-1.5 text-sm text-red-600">
          {error}
        </p>
      ) : (
        hint && <p className="mt-1.5 text-xs text-stone-500">{hint}</p>
      )}
    </div>
  );
}
