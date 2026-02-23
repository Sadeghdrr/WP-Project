/**
 * Alert — inline notification banner for contextual messages.
 */
import type { ReactNode } from 'react';

export interface AlertProps {
  children: ReactNode;
  type?: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  onClose?: () => void;
  className?: string;
}

export function Alert({
  children,
  type = 'info',
  title,
  onClose,
  className = '',
}: AlertProps) {
  return (
    <div className={`alert alert--${type} ${className}`} role="alert">
      <div className="alert__content">
        {title && <strong className="alert__title">{title}</strong>}
        <div className="alert__message">{children}</div>
      </div>
      {onClose && (
        <button className="alert__close" onClick={onClose} aria-label="Dismiss">
          ×
        </button>
      )}
    </div>
  );
}
