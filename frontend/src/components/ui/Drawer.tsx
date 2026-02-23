/**
 * Drawer — slide-in panel overlay from left or right.
 */
import { useEffect, useCallback, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  position?: 'left' | 'right';
  size?: 'sm' | 'md' | 'lg';
}

export function Drawer({
  open,
  onClose,
  title,
  children,
  position = 'right',
  size = 'md',
}: DrawerProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return createPortal(
    <div className="drawer-overlay" onClick={onClose} role="presentation">
      <div
        className={`drawer drawer--${position} drawer--${size}`}
        role="dialog"
        aria-modal="true"
        aria-label={title ?? 'Drawer'}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="drawer__header">
            <h2 className="drawer__title">{title}</h2>
            <button
              className="drawer__close"
              onClick={onClose}
              aria-label="Close"
            >
              ×
            </button>
          </div>
        )}
        <div className="drawer__body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
