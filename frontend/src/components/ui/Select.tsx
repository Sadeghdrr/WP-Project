/**
 * Select — native dropdown with label and validation styling.
 */
import { useId, type SelectHTMLAttributes } from 'react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label?: string;
  options: SelectOption[];
  error?: string;
  placeholder?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Select({
  label,
  options,
  error,
  placeholder,
  size = 'md',
  className = '',
  id: providedId,
  ...rest
}: SelectProps) {
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
      <select
        id={id}
        className="form-field__input form-field__select"
        aria-invalid={!!error}
        {...rest}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} disabled={opt.disabled}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <span className="form-field__error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
