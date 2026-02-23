/**
 * Input & Textarea — form field primitives with label, error, and hint.
 */
import {
  useId,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react';

/* ── Input ───────────────────────────────────────────────────────── */

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  error?: string;
  hint?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Input({
  label,
  error,
  hint,
  size = 'md',
  className = '',
  id: providedId,
  ...rest
}: InputProps) {
  const generatedId = useId();
  const id = providedId ?? generatedId;

  const fieldClasses = [
    'form-field',
    error && 'form-field--error',
    `form-field--${size}`,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={fieldClasses}>
      {label && (
        <label htmlFor={id} className="form-field__label">
          {label}
          {rest.required && <span className="form-field__required">*</span>}
        </label>
      )}
      <input
        id={id}
        className="form-field__input"
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        {...rest}
      />
      {error && (
        <span id={`${id}-error`} className="form-field__error" role="alert">
          {error}
        </span>
      )}
      {hint && !error && <span className="form-field__hint">{hint}</span>}
    </div>
  );
}

/* ── Textarea ────────────────────────────────────────────────────── */

export interface TextareaProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'size'> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Textarea({
  label,
  error,
  hint,
  className = '',
  id: providedId,
  ...rest
}: TextareaProps) {
  const generatedId = useId();
  const id = providedId ?? generatedId;

  return (
    <div
      className={`form-field ${error ? 'form-field--error' : ''} ${className}`}
    >
      {label && (
        <label htmlFor={id} className="form-field__label">
          {label}
          {rest.required && <span className="form-field__required">*</span>}
        </label>
      )}
      <textarea
        id={id}
        className="form-field__input form-field__textarea"
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        {...rest}
      />
      {error && (
        <span id={`${id}-error`} className="form-field__error" role="alert">
          {error}
        </span>
      )}
      {hint && !error && <span className="form-field__hint">{hint}</span>}
    </div>
  );
}
