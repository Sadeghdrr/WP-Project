/**
 * Card — container with optional header, actions, and footer.
 */
import type { ReactNode } from 'react';

export interface CardProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  footer?: ReactNode;
  padding?: boolean;
  hoverable?: boolean;
  className?: string;
}

export function Card({
  children,
  title,
  subtitle,
  actions,
  footer,
  padding = true,
  hoverable = false,
  className = '',
}: CardProps) {
  return (
    <div
      className={`card ${hoverable ? 'card--hoverable' : ''} ${className}`}
    >
      {(title || actions) && (
        <div className="card__header">
          <div>
            {title && <h3 className="card__title">{title}</h3>}
            {subtitle && <p className="card__subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="card__actions">{actions}</div>}
        </div>
      )}
      <div className={padding ? 'card__body' : 'card__body card__body--flush'}>
        {children}
      </div>
      {footer && <div className="card__footer">{footer}</div>}
    </div>
  );
}
