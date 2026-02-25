/**
 * FieldError — inline validation error shown below form fields.
 *
 * Usage:
 *   <input name="email" ... />
 *   <FieldError error={apiError} field="email" />
 */

import type { ApiError } from "../../api/client";
import { getFieldErrors } from "../../lib/errors";
import styles from "./FieldError.module.css";

export interface FieldErrorProps {
  /** The normalised API error. */
  error?: ApiError | null;
  /** Field name to extract errors for. */
  field: string;
  /** Additional class. */
  className?: string;
}

export default function FieldError({ error, field, className }: FieldErrorProps) {
  const messages = getFieldErrors(error, field);
  if (messages.length === 0) return null;

  return (
    <div className={`${styles.wrapper} ${className ?? ""}`.trim()} role="alert">
      {messages.map((msg, i) => (
        <p key={i} className={styles.message}>
          {msg}
        </p>
      ))}
    </div>
  );
}
