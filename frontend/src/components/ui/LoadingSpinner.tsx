/**
 * LoadingSpinner — a simple CSS-only loading indicator.
 *
 * Variants:
 *   - "page"   → centered full-area spinner (default)
 *   - "inline" → small inline spinner for buttons/labels
 */

import styles from "./LoadingSpinner.module.css";

export interface LoadingSpinnerProps {
  /** Display variant. */
  variant?: "page" | "inline";
  /** Accessible label (defaults to "Loading…"). */
  label?: string;
  /** Optional className for the outer wrapper. */
  className?: string;
}

export default function LoadingSpinner({
  variant = "page",
  label = "Loading\u2026",
  className,
}: LoadingSpinnerProps) {
  const isPage = variant === "page";

  return (
    <div
      className={`${isPage ? styles.page : styles.inline} ${className ?? ""}`.trim()}
      role="status"
      aria-label={label}
    >
      <div className={isPage ? styles.spinnerLg : styles.spinnerSm} />
      {isPage && <span className={styles.label}>{label}</span>}
    </div>
  );
}
