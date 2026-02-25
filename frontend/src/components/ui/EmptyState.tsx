/**
 * EmptyState — shown when a list or view has no data to display.
 *
 * Usage:
 *   <EmptyState title="No cases found" />
 *   <EmptyState
 *     title="No results"
 *     description="Try adjusting your filters."
 *     action={{ label: "Clear filters", onClick: reset }}
 *   />
 */

import styles from "./EmptyState.module.css";

export interface EmptyStateProps {
  /** Primary heading. */
  title: string;
  /** Optional explanatory text. */
  description?: string;
  /** Optional action button. */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Optional icon/emoji displayed above the title. */
  icon?: string;
  /** Additional class. */
  className?: string;
}

export default function EmptyState({
  title,
  description,
  action,
  icon = "📭",
  className,
}: EmptyStateProps) {
  return (
    <div className={`${styles.wrapper} ${className ?? ""}`.trim()}>
      <span className={styles.icon} aria-hidden="true">
        {icon}
      </span>
      <h3 className={styles.title}>{title}</h3>
      {description && <p className={styles.description}>{description}</p>}
      {action && (
        <button className={styles.action} onClick={action.onClick} type="button">
          {action.label}
        </button>
      )}
    </div>
  );
}
