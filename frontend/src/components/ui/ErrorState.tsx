/**
 * ErrorState — shown when a request or operation fails.
 *
 * Renders the normalised `ApiError` from the API client
 * in a user-friendly way, with optional retry action.
 *
 * Usage:
 *   <ErrorState error={apiError} onRetry={refetch} />
 *   <ErrorState message="Something went wrong" />
 */

import type { ApiError } from "../../api/client";
import { flattenErrors } from "../../lib/errors";
import styles from "./ErrorState.module.css";

export interface ErrorStateProps {
  /** Normalised API error object. */
  error?: ApiError | null;
  /** Override message (used when no ApiError is available). */
  message?: string;
  /** Optional retry callback — renders a "Try again" button. */
  onRetry?: () => void;
  /** Compact mode for inline display (no min-height). */
  compact?: boolean;
  /** Additional class. */
  className?: string;
}

export default function ErrorState({
  error,
  message,
  onRetry,
  compact = false,
  className,
}: ErrorStateProps) {
  const msgs = error ? flattenErrors(error) : [];
  const displayMessage =
    message ?? (msgs.length > 0 ? msgs[0] : "An unexpected error occurred.");
  const extraMessages = message ? msgs : msgs.slice(1);

  return (
    <div
      className={`${compact ? styles.compact : styles.wrapper} ${className ?? ""}`.trim()}
      role="alert"
    >
      <span className={styles.icon} aria-hidden="true">
        ⚠️
      </span>
      <p className={styles.message}>{displayMessage}</p>
      {extraMessages.length > 0 && (
        <ul className={styles.details}>
          {extraMessages.map((msg, i) => (
            <li key={i}>{msg}</li>
          ))}
        </ul>
      )}
      {onRetry && (
        <button className={styles.retry} onClick={onRetry} type="button">
          Try again
        </button>
      )}
    </div>
  );
}
